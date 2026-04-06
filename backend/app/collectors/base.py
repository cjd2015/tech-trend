from abc import ABC, abstractmethod
from typing import List, Dict, Any
import httpx
import datetime
import re


class BaseCollector(ABC):
    """信号采集器基类"""

    def __init__(self, source_type: str, source_name: str):
        self.source_type = source_type
        self.source_name = source_name

    @abstractmethod
    async def collect(self) -> List[Dict[str, Any]]:
        """采集信号数据，返回标准化字典列表"""
        pass

    def _create_signal_dict(self, external_id: str, **kwargs) -> Dict[str, Any]:
        """创建标准化的信号字典"""
        return {
            "source_type": self.source_type,
            "source_name": self.source_name,
            "external_id": external_id,
            "fetched_at": datetime.datetime.utcnow(),
            **kwargs
        }

    def _get_browser_headers(self, referer: str | None = None, extra_headers: Dict[str, str] | None = None) -> Dict[str, str]:
        """构造更接近真实浏览器的请求头，降低被站点直接拦截的概率。"""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
        }
        if referer:
            headers["Referer"] = referer
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _create_http_client(
        self,
        referer: str | None = None,
        timeout: float = 30.0,
        extra_headers: Dict[str, str] | None = None,
    ) -> httpx.AsyncClient:
        """创建带浏览器头和重定向支持的 HTTP 客户端。"""
        return httpx.AsyncClient(
            headers=self._get_browser_headers(referer=referer, extra_headers=extra_headers),
            follow_redirects=True,
            timeout=timeout,
        )

    async def _run_with_playwright(
        self,
        url: str,
        handler,
        *,
        timeout_ms: int = 45000,
    ):
        """使用 Playwright 以真实浏览器形式打开页面并执行回调。"""
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is not installed") from exc

        async with async_playwright() as playwright:
            browser = None
            launch_kwargs = {
                "headless": True,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            }

            for channel in ("msedge", "chrome", None):
                try:
                    if channel:
                        browser = await playwright.chromium.launch(channel=channel, **launch_kwargs)
                    else:
                        browser = await playwright.chromium.launch(**launch_kwargs)
                    break
                except Exception:
                    browser = None

            if browser is None:
                raise RuntimeError("No Playwright browser executable is available")

            context = await browser.new_context(
                user_agent=self._get_browser_headers().get("User-Agent"),
                locale="en-US",
                viewport={"width": 1440, "height": 900},
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                },
            )
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                await page.wait_for_timeout(1200)
                return await handler(page)
            finally:
                await context.close()
                await browser.close()

    def _normalize_text(self, value: str | None) -> str:
        """压缩网页抓取文本中的多余空白。"""
        return re.sub(r"\s+", " ", (value or "")).strip()
