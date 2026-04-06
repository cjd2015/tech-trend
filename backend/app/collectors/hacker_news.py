import httpx
import json
import datetime
from typing import List, Dict, Any
from .base import BaseCollector

class HackerNewsCollector(BaseCollector):
    """Hacker News 信号采集器"""

    def __init__(self):
        super().__init__("community", "hacker_news")
        self.base_url = "https://hacker-news.firebaseio.com/v0"

    async def collect(self) -> List[Dict[str, Any]]:
        """采集热门故事"""
        signals = []

        async with self._create_http_client(referer="https://news.ycombinator.com/") as client:
            # 获取热门故事ID
            response = await client.get(f"{self.base_url}/topstories.json")
            if response.status_code != 200:
                return signals

            story_ids = response.json()[:10]  # 取前10个热门故事

            # 获取每个故事详情
            for story_id in story_ids:
                try:
                    story_response = await client.get(f"{self.base_url}/item/{story_id}.json")
                    if story_response.status_code == 200:
                        story = story_response.json()

                        signal = self._create_signal_dict(
                            external_id=str(story_id),
                            title=story.get("title", ""),
                            url=story.get("url", ""),
                            content=story.get("text", ""),
                            author=story.get("by", ""),
                            published_at=datetime.datetime.fromtimestamp(story.get("time", 0)) if story.get("time") else None,
                            metadata_json=json.dumps({
                                "score": story.get("score", 0),
                                "descendants": story.get("descendants", 0),
                                "type": story.get("type", "story")
                            })
                        )
                        signals.append(signal)

                except Exception as e:
                    print(f"Error collecting story {story_id}: {e}")
                    continue

        return signals
