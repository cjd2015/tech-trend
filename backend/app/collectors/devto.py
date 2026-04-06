import httpx
import json
import datetime
from typing import List, Dict, Any
from .base import BaseCollector

class DevToCollector(BaseCollector):
    """Dev.to 文章采集器"""

    def __init__(self):
        super().__init__("community", "devto")
        self.base_url = "https://dev.to/api"
        self.top_url = "https://dev.to/top/week"

    async def collect(self) -> List[Dict[str, Any]]:
        """采集 Dev.to 热门文章，优先使用浏览器采集。"""
        try:
            signals = await self._collect_with_playwright()
            if signals:
                return signals
            print("Playwright Dev.to returned 0 items, fallback to API")
        except Exception as e:
            print(f"Playwright Dev.to failed, fallback to API: {e}")
        return await self._collect_with_api()

    async def _collect_with_playwright(self) -> List[Dict[str, Any]]:
        async def handler(page) -> List[Dict[str, Any]]:
            signals = []
            cards = page.locator("article")
            count = min(await cards.count(), 10)

            for index in range(count):
                card = cards.nth(index)
                title_link = card.locator("h2 a, h3 a").first
                if await title_link.count() == 0:
                    continue

                href = await title_link.get_attribute("href")
                title = self._normalize_text(await title_link.inner_text())
                if not title:
                    continue

                description = ""
                if await card.locator("p").count():
                    description = self._normalize_text(await card.locator("p").first.text_content())

                author = ""
                author_candidates = [
                    'a[href^="/"][data-testid*="user"], a.crayons-story__secondary',
                    'a[href^="/"]',
                ]
                for selector in author_candidates:
                    locator = card.locator(selector)
                    if await locator.count():
                        author = self._normalize_text(await locator.first.text_content())
                        if author and author.lower() != title.lower():
                            break

                time_locator = card.locator("time").first
                published_at = datetime.datetime.utcnow()
                if await time_locator.count():
                    time_value = await time_locator.get_attribute("datetime")
                    if time_value:
                        published_at = datetime.datetime.fromisoformat(time_value.replace("Z", "+00:00"))

                url = href or ""
                if url.startswith("/"):
                    url = f"https://dev.to{url}"

                signal = self._create_signal_dict(
                    external_id=url or title,
                    title=title,
                    url=url,
                    content=description,
                    author=author,
                    published_at=published_at,
                    metadata_json=json.dumps({
                        "source": "devto_browser",
                    }),
                )
                signals.append(signal)

            return signals

        return await self._run_with_playwright(self.top_url, handler)

    async def _collect_with_api(self) -> List[Dict[str, Any]]:
        signals = []
        params = {
            "per_page": 10,
            "top": 7,
        }

        async with self._create_http_client(
            referer="https://dev.to/",
            extra_headers={"Accept": "application/json, text/plain, */*"},
        ) as client:
            response = await client.get(f"{self.base_url}/articles", params=params)
            if response.status_code != 200:
                return signals

            articles = response.json()
            for article in articles:
                signal = self._create_signal_dict(
                    external_id=str(article["id"]),
                    title=article["title"],
                    url=article["url"],
                    content=article.get("description", ""),
                    author=article["user"]["name"],
                    published_at=datetime.datetime.fromisoformat(article["published_at"].replace('Z', '+00:00')),
                    metadata_json=json.dumps({
                        "positive_reactions_count": article["positive_reactions_count"],
                        "comments_count": article["comments_count"],
                        "reading_time_minutes": article["reading_time_minutes"],
                        "tags": article["tag_list"],
                        "cover_image": article.get("cover_image", ""),
                        "source": "devto_api",
                    }),
                )
                signals.append(signal)

        return signals
