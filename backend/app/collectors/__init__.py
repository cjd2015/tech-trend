from .hacker_news import HackerNewsCollector
from .arxiv import ArxivCollector
from .patent import PatentCollector
from .technical_book import TechnicalBookCollector
from .github_trending import GitHubTrendingCollector
from .reddit_tech import RedditTechCollector
from .stackoverflow import StackOverflowCollector
from .devto import DevToCollector
from .producthunt import ProductHuntCollector
from .techcrunch import TechCrunchCollector
from .base import BaseCollector

# 采集器注册表
COLLECTORS = {
    "hacker_news": HackerNewsCollector,
    "arxiv": ArxivCollector,
    "patent": PatentCollector,
    "technical_book": TechnicalBookCollector,
    "github_trending": GitHubTrendingCollector,
    "reddit_tech": RedditTechCollector,
    "stackoverflow": StackOverflowCollector,
    "devto": DevToCollector,
    "producthunt": ProductHuntCollector,
    "techcrunch": TechCrunchCollector,
}

def get_collector(name: str) -> BaseCollector:
    """获取采集器实例"""
    collector_class = COLLECTORS.get(name)
    if not collector_class:
        raise ValueError(f"Unknown collector: {name}")
    return collector_class()

def list_collectors() -> list[str]:
    """列出所有可用的采集器名称"""
    return list(COLLECTORS.keys())


def list_collectors() -> list[str]:
    """返回已注册的采集器名称列表"""
    return list(COLLECTORS.keys())
