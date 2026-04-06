import httpx
import json
import datetime
from typing import List, Dict, Any
import feedparser
from .base import BaseCollector

class TechCrunchCollector(BaseCollector):
    """TechCrunch 新闻采集器"""

    def __init__(self):
        super().__init__("industry", "techcrunch")
        self.rss_url = "https://techcrunch.com/feed/"

    async def collect(self) -> List[Dict[str, Any]]:
        """采集TechCrunch最新文章"""
        signals = []

        async with self._create_http_client(referer="https://techcrunch.com/", timeout=30.0) as client:
            try:
                response = await client.get(self.rss_url)
                response.raise_for_status()

                # 解析RSS feed
                feed = feedparser.parse(response.text)

                for entry in feed.entries[:10]:  # 限制为前10个
                    # 提取标题和描述
                    title = entry.title if hasattr(entry, 'title') else 'Unknown Title'
                    description = entry.description if hasattr(entry, 'description') else ''

                    # 清理HTML标签
                    import re
                    description = re.sub(r'<[^>]+>', '', description)

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
                        author=entry.author if hasattr(entry, 'author') else 'TechCrunch',
                        published_at=published_at,
                        metadata_json=json.dumps({
                            "source": "techcrunch_rss",
                            "feed_title": feed.feed.title if hasattr(feed.feed, 'title') else 'TechCrunch'
                        })
                    )
                    signals.append(signal)

            except Exception as e:
                import traceback
                print(f"Error collecting TechCrunch: {e}")
                traceback.print_exc()

        return signals
