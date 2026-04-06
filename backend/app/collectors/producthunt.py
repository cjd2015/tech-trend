import httpx
import json
import datetime
from typing import List, Dict, Any
import feedparser
from .base import BaseCollector

class ProductHuntCollector(BaseCollector):
    """Product Hunt 产品采集器"""

    def __init__(self):
        super().__init__("industry", "producthunt")
        self.rss_url = "https://www.producthunt.com/feed"

    async def collect(self) -> List[Dict[str, Any]]:
        """采集Product Hunt今日热门产品"""
        signals = []

        async with self._create_http_client(referer="https://www.producthunt.com/") as client:
            try:
                response = await client.get(self.rss_url)
                response.raise_for_status()

                # 解析RSS feed
                feed = feedparser.parse(response.text)

                for entry in feed.entries[:10]:  # 限制为前10个
                    # 提取标题和描述
                    title = entry.title if hasattr(entry, 'title') else 'Unknown Title'
                    description = entry.description if hasattr(entry, 'description') else ''
                    link = entry.link if hasattr(entry, 'link') else ''

                    # 解析发布日期
                    published_at = datetime.datetime.now()  # 默认当前时间
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_at = datetime.datetime(*entry.published_parsed[:6])

                    # 创建信号
                    signal = self._create_signal_dict(
                        external_id=entry.id if hasattr(entry, 'id') else link,
                        title=title,
                        url=link,
                        content=description,
                        author=entry.author if hasattr(entry, 'author') else 'Product Hunt',
                        published_at=published_at,
                        metadata_json=json.dumps({
                            "source": "producthunt_rss",
                            "feed_title": feed.feed.title if hasattr(feed.feed, 'title') else 'Product Hunt'
                        })
                    )
                    signals.append(signal)

            except Exception as e:
                print(f"Error collecting Product Hunt: {e}")

        return signals
