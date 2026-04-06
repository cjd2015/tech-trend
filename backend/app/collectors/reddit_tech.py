import httpx
import json
import datetime
from typing import List, Dict, Any
from .base import BaseCollector

class RedditTechCollector(BaseCollector):
    """Reddit r/technology 信号采集器"""

    def __init__(self):
        super().__init__("community", "reddit_tech")
        self.hot_url = "https://old.reddit.com/r/technology/hot/"

    async def collect(self) -> List[Dict[str, Any]]:
        """采集 Reddit 热门帖子，优先使用 Playwright 浏览器抓取。"""
        try:
            signals = await self._collect_with_playwright()
            if signals:
                return signals
            print("Playwright Reddit returned 0 items, fallback to curated posts")
        except Exception as e:
            print(f"Playwright Reddit failed, fallback to curated posts: {e}")
        return self._collect_curated_fallback()

    async def _collect_with_playwright(self) -> List[Dict[str, Any]]:
        async def handler(page) -> List[Dict[str, Any]]:
            signals = []
            posts = page.locator("div.thing")
            count = min(await posts.count(), 10)

            for index in range(count):
                post = posts.nth(index)
                post_id = await post.get_attribute("data-fullname")
                title_locator = post.locator("a.title").first
                if await title_locator.count() == 0:
                    continue

                title = self._normalize_text(await title_locator.text_content())
                url = await title_locator.get_attribute("href") or ""
                author = self._normalize_text(await post.locator("a.author").first.text_content()) if await post.locator("a.author").count() else ""
                comments_text = self._normalize_text(await post.locator("a.comments").first.text_content()) if await post.locator("a.comments").count() else ""
                score_text = self._normalize_text(await post.locator("div.score.unvoted").first.text_content()) if await post.locator("div.score.unvoted").count() else ""

                published_at = datetime.datetime.utcnow()
                time_locator = post.locator("time").first
                if await time_locator.count():
                    time_value = await time_locator.get_attribute("datetime")
                    if time_value:
                        published_at = datetime.datetime.fromisoformat(time_value.replace("Z", "+00:00"))

                signal = self._create_signal_dict(
                    external_id=post_id or url or title,
                    title=title,
                    url=url,
                    content="",
                    author=author,
                    published_at=published_at,
                    metadata_json=json.dumps({
                        "score": score_text,
                        "comments": comments_text,
                        "source": "reddit_old_browser",
                    }),
                )
                signals.append(signal)

            return signals

        return await self._run_with_playwright(self.hot_url, handler)

    def _collect_curated_fallback(self) -> List[Dict[str, Any]]:
        signals = []
        popular_posts = [
            {
                "id": "reddit_fallback_1",
                "title": "Technology community fallback item",
                "url": "https://reddit.com/r/technology/",
                "content": "Fallback Reddit signal when browser scraping is unavailable.",
                "author": "system_fallback",
                "created_utc": datetime.datetime.now().timestamp() - 3600,
                "score": 0,
                "num_comments": 0,
            }
        ]

        for post in popular_posts:
            signal = self._create_signal_dict(
                external_id=post["id"],
                title=post["title"],
                url=post["url"],
                content=post["content"],
                author=post["author"],
                published_at=datetime.datetime.fromtimestamp(post["created_utc"]),
                metadata_json=json.dumps({
                    "score": post["score"],
                    "num_comments": post["num_comments"],
                    "source": "curated_reddit_posts",
                }),
            )
            signals.append(signal)

        return signals
