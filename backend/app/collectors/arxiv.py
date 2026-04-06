import httpx
import feedparser
import datetime
from typing import List, Dict, Any
from .base import BaseCollector

class ArxivCollector(BaseCollector):
    """arXiv 学术论文信号采集器"""

    def __init__(self):
        super().__init__("research", "arxiv")
        # 关注计算机科学领域的新论文
        self.categories = [
            "cs.AI",      # Artificial Intelligence
            "cs.CL",      # Computation and Language
            "cs.CV",      # Computer Vision and Pattern Recognition
            "cs.LG",      # Machine Learning
            "cs.NE",      # Neural and Evolutionary Computing
            "cs.RO",      # Robotics
            "cs.SE",      # Software Engineering
            "cs.DC",      # Distributed Computing
            "cs.CR",      # Cryptography and Security
            "cs.HC",      # Human-Computer Interaction
        ]

    async def collect(self) -> List[Dict[str, Any]]:
        """采集近期热门论文"""
        signals = []

        for category in self.categories:
            try:
                # 获取最近7天的论文
                rss_url = f"http://export.arxiv.org/rss/{category}"
                async with self._create_http_client(referer="https://arxiv.org/", timeout=30.0) as client:
                    response = await client.get(rss_url, timeout=30)

                if response.status_code != 200:
                    continue

                # 解析RSS feed
                feed = feedparser.parse(response.text)

                for entry in feed.entries[:5]:  # 每个分类取前5篇
                    # 提取arXiv ID
                    arxiv_id = self._extract_arxiv_id(entry.link)

                    signal = self._create_signal_dict(
                        external_id=arxiv_id,
                        title=entry.title,
                        url=entry.link,
                        content=getattr(entry, 'summary', ''),
                        author=self._extract_authors(entry),
                        published_at=self._parse_published_date(entry),
                        metadata_json=self._create_metadata(entry, category)
                    )
                    signals.append(signal)

            except Exception as e:
                print(f"Error collecting arXiv category {category}: {e}")
                continue

        return signals

    def _extract_arxiv_id(self, url: str) -> str:
        """从URL中提取arXiv ID"""
        # URL格式: http://arxiv.org/abs/2404.01234
        parts = url.split('/')
        if len(parts) >= 3 and parts[-2] == 'abs':
            return parts[-1]
        return url.split('/')[-1]

    def _extract_authors(self, entry) -> str:
        """提取作者信息"""
        if hasattr(entry, 'authors'):
            authors = []
            for author in entry.authors:
                if hasattr(author, 'name'):
                    authors.append(author.name)
                elif isinstance(author, str):
                    authors.append(author)
            return ', '.join(authors)
        return "Unknown"

    def _parse_published_date(self, entry) -> datetime.datetime:
        """解析发布日期"""
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            return datetime.datetime(*entry.published_parsed[:6])
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            return datetime.datetime(*entry.updated_parsed[:6])
        return datetime.datetime.utcnow()

    def _create_metadata(self, entry, category: str) -> str:
        """创建元数据JSON"""
        import json

        metadata = {
            "category": category,
            "arxiv_id": self._extract_arxiv_id(entry.link),
            "comment": getattr(entry, 'arxiv_comment', ''),
            "primary_category": category,
            "source": "arxiv_rss"
        }
        return json.dumps(metadata)
