import httpx
import json
import datetime
from typing import List, Dict, Any
from .base import BaseCollector

class StackOverflowCollector(BaseCollector):
    """Stack Overflow 热门问题采集器"""

    def __init__(self):
        super().__init__("community", "stackoverflow")
        self.base_url = "https://api.stackexchange.com/2.3"

    async def collect(self) -> List[Dict[str, Any]]:
        """采集Stack Overflow热门问题"""
        signals = []

        params = {
            "order": "desc",
            "sort": "hot",
            "site": "stackoverflow",
            "pagesize": 10
            # Removed tagged parameter as it was too restrictive
        }

        async with self._create_http_client(
            referer="https://stackoverflow.com/questions",
            extra_headers={"Accept": "application/json, text/plain, */*"},
        ) as client:
            try:
                response = await client.get(f"{self.base_url}/questions", params=params)
                if response.status_code == 200:
                    data = response.json()
                    for question in data.get("items", []):
                        signal = self._create_signal_dict(
                            external_id=str(question["question_id"]),
                            title=question["title"],
                            url=question["link"],
                            content="",  # Stack Overflow questions don't have body in this API
                            author=question.get("owner", {}).get("display_name", ""),
                            published_at=datetime.datetime.fromtimestamp(question["creation_date"]),
                            metadata_json=json.dumps({
                                "score": question["score"],
                                "answer_count": question["answer_count"],
                                "view_count": question["view_count"],
                                "tags": question["tags"],
                                "is_answered": question["is_answered"]
                            })
                        )
                        signals.append(signal)
            except Exception as e:
                print(f"Error collecting Stack Overflow: {e}")

        return signals
