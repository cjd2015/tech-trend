import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
PRIVATE_DOCS_ROOT = REPO_ROOT / ".private" / "docs"
MANIFEST_PATH = PRIVATE_DOCS_ROOT / "release" / "release-manifest.json"


def run_git(*args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()
    except subprocess.CalledProcessError as exc:
        return exc.stdout.strip() or exc.stderr.strip()


def sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_files() -> list[dict]:
    include_roots = [
        REPO_ROOT / "backend" / "app",
        REPO_ROOT / "frontend" / "src",
        PRIVATE_DOCS_ROOT,
    ]
    include_files = [
        REPO_ROOT / "backend" / "requirements.txt",
        REPO_ROOT / "frontend" / "package.json",
        REPO_ROOT / "frontend" / "package-lock.json",
        REPO_ROOT / "frontend" / "vite.config.js",
        REPO_ROOT / "frontend" / "index.html",
        REPO_ROOT / "README.md",
        REPO_ROOT / "scripts" / "generate_release_manifest.py",
    ]

    files: list[Path] = []
    for root in include_roots:
        if root.exists():
            files.extend(path for path in root.rglob("*") if path.is_file())
    for file_path in include_files:
        if file_path.exists():
            files.append(file_path)

    manifest_files = []
    for path in sorted(set(files)):
        manifest_files.append(
            {
                "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "size": path.stat().st_size,
                "sha256": sha256_for_file(path),
            }
        )
    return manifest_files


def collect_databases() -> list[dict]:
    db_paths = [
        REPO_ROOT / "crucix_refactor.db",
        REPO_ROOT / "backend" / "crucix_refactor.db",
        REPO_ROOT / "backend" / "app" / "crucix_refactor.db",
    ]

    databases = []
    for path in db_paths:
        if not path.exists():
            continue
        stat = path.stat()
        databases.append(
            {
                "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "size": stat.st_size,
                "last_modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "sha256": sha256_for_file(path),
            }
        )
    return databases


def collect_routes() -> list[dict]:
    sys.path.insert(0, str(BACKEND_DIR))
    from app.main import app  # noqa: WPS433

    routes = []
    for route in app.routes:
        methods = sorted(list(getattr(route, "methods", []) or []))
        path = getattr(route, "path", None)
        name = getattr(route, "name", None)
        if not path:
            continue
        routes.append(
            {
                "path": path,
                "methods": methods,
                "name": name,
            }
        )
    return routes


def collect_frontend_dependencies() -> dict:
    package_json = json.loads((REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    return {
        "name": package_json["name"],
        "version": package_json["version"],
        "dependencies": package_json.get("dependencies", {}),
        "devDependencies": package_json.get("devDependencies", {}),
    }


def collect_backend_dependencies() -> list[str]:
    requirements_path = REPO_ROOT / "backend" / "requirements.txt"
    return [
        line.strip()
        for line in requirements_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def build_manifest() -> dict:
    return {
        "product": "Tech Trend",
        "manifest_generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git": {
            "head_commit": run_git("rev-parse", "HEAD"),
            "worktree_clean": run_git("status", "--short") == "",
        },
        "runtime": {
            "frontend_dev": {
                "host": "localhost",
                "port": 5173,
                "proxy_backend": "http://localhost:8000",
            },
            "backend_api": {
                "host": "127.0.0.1",
                "port": 8000,
                "database_url_default": "sqlite:///./crucix_refactor.db",
            },
        },
        "dependencies": {
            "backend": collect_backend_dependencies(),
            "frontend": collect_frontend_dependencies(),
        },
        "databases": collect_databases(),
        "api_routes": collect_routes(),
        "tracked_files": collect_files(),
    }


def main() -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest()
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(MANIFEST_PATH)


if __name__ == "__main__":
    main()
