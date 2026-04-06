import httpx
import json
import datetime
from typing import List, Dict, Any
from .base import BaseCollector

class GitHubTrendingCollector(BaseCollector):
    """GitHub Trending 信号采集器"""

    def __init__(self):
        super().__init__("community", "github_trending")
        self.base_url = "https://api.github.com/search/repositories"
        self.trending_url = "https://github.com/trending"

    async def collect(self) -> List[Dict[str, Any]]:
        """采集 GitHub Trending 仓库，优先使用浏览器采集。"""
        try:
            signals = await self._collect_with_playwright()
            if signals:
                return signals
            print("Playwright GitHub trending returned 0 items, fallback to API")
        except Exception as e:
            print(f"Playwright GitHub trending failed, fallback to API: {e}")
        return await self._collect_with_api()

    async def _collect_with_playwright(self) -> List[Dict[str, Any]]:
        async def handler(page) -> List[Dict[str, Any]]:
            signals = []
            rows = page.locator("article.Box-row")
            count = min(await rows.count(), 10)

            for index in range(count):
                row = rows.nth(index)
                link = row.locator("h2 a").first
                href = await link.get_attribute("href")
                full_name = self._normalize_text(await link.inner_text())
                repo_url = f"https://github.com{href}" if href else ""
                description = self._normalize_text(await row.locator("p").first.text_content()) if await row.locator("p").count() else ""
                language = self._normalize_text(await row.locator('[itemprop="programmingLanguage"]').first.text_content()) if await row.locator('[itemprop="programmingLanguage"]').count() else ""
                stars = self._normalize_text(await row.locator('a[href*="/stargazers"]').first.text_content()) if await row.locator('a[href*="/stargazers"]').count() else ""

                owner = ""
                repo_name = full_name
                if "/" in full_name:
                    owner, repo_name = [part.strip() for part in full_name.split("/", 1)]

                signal = self._create_signal_dict(
                    external_id=full_name or repo_url,
                    title=repo_name or full_name or "Unknown Repository",
                    url=repo_url,
                    content=description,
                    author=owner,
                    published_at=datetime.datetime.utcnow(),
                    metadata_json=json.dumps({
                        "stars": stars,
                        "language": language,
                        "source": "github_trending_browser",
                    }),
                )
                signals.append(signal)

            return signals

        return await self._run_with_playwright(self.trending_url, handler)

    async def _collect_with_api(self) -> List[Dict[str, Any]]:
        signals = []
        query = "stars:>100 created:>2024-01-01 language:python,javascript,typescript,go,rust"
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 10,
        }

        async with self._create_http_client(
            referer="https://github.com/trending",
            extra_headers={
                "Accept": "application/vnd.github+json, application/json;q=0.9, */*;q=0.8",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        ) as client:
            response = await client.get(self.base_url, params=params)
            if response.status_code != 200:
                return signals

            data = response.json()
            for repo in data.get("items", []):
                signal = self._create_signal_dict(
                    external_id=str(repo["id"]),
                    title=repo["name"],
                    url=repo["html_url"],
                    content=repo["description"] or "",
                    author=repo["owner"]["login"],
                    published_at=datetime.datetime.fromisoformat(repo["created_at"].replace('Z', '+00:00')),
                    metadata_json=json.dumps({
                        "stars": repo["stargazers_count"],
                        "forks": repo["forks_count"],
                        "language": repo["language"],
                        "topics": repo.get("topics", []),
                        "source": "github_search_api",
                    }),
                )
                signals.append(signal)

        return signals
