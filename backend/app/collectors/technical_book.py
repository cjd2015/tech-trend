import httpx
import json
import datetime
from typing import List, Dict, Any
from .base import BaseCollector

class TechnicalBookCollector(BaseCollector):
    """技术书籍信号采集器"""

    def __init__(self):
        super().__init__("knowledge", "technical_book")

    async def collect(self) -> List[Dict[str, Any]]:
        """采集近期技术书籍"""
        signals = []

        # 预定义的热门技术书籍列表（由于Google Books API可能被屏蔽）
        popular_books = [
            {
                "title": "Deep Learning",
                "authors": ["Ian Goodfellow", "Yoshua Bengio", "Aaron Courville"],
                "description": "The definitive textbook on deep learning, covering the theory and practice of neural networks.",
                "published_date": "2016-11-18",
                "isbn": "9780262035613",
                "url": "https://www.deeplearningbook.org/"
            },
            {
                "title": "Hands-On Machine Learning with Scikit-Learn, Keras, and TensorFlow",
                "authors": ["Aurélien Géron"],
                "description": "A practical guide to machine learning using popular Python libraries.",
                "published_date": "2019-09-05",
                "isbn": "9781492032649",
                "url": "https://www.oreilly.com/library/view/hands-on-machine-learning/9781492032632/"
            },
            {
                "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
                "authors": ["Robert C. Martin"],
                "description": "A guide to writing clean, maintainable code following best practices.",
                "published_date": "2008-08-01",
                "isbn": "9780132350884",
                "url": "https://www.oreilly.com/library/view/clean-code/9780136083238/"
            },
            {
                "title": "The Pragmatic Programmer",
                "authors": ["Andrew Hunt", "David Thomas"],
                "description": "A collection of practical advice for software developers.",
                "published_date": "1999-10-20",
                "isbn": "9780201616224",
                "url": "https://pragprog.com/titles/tpp20/the-pragmatic-programmer-20th-anniversary-edition/"
            },
            {
                "title": "Designing Data-Intensive Applications",
                "authors": ["Martin Kleppmann"],
                "description": "A comprehensive guide to building reliable, scalable, and maintainable data systems.",
                "published_date": "2017-03-16",
                "isbn": "9781449373320",
                "url": "https://dataintensive.net/"
            },
            {
                "title": "Computer Systems: A Programmer's Perspective",
                "authors": ["Randal E. Bryant", "David R. O'Hallaron"],
                "description": "An introduction to computer systems from the programmer's perspective.",
                "published_date": "2015-03-01",
                "isbn": "9780134092669",
                "url": "https://www.amazon.com/Computer-Systems-Programmers-Perspective-3rd/dp/013409266X"
            },
            {
                "title": "Introduction to Algorithms",
                "authors": ["Thomas H. Cormen", "Charles E. Leiserson", "Ronald L. Rivest", "Clifford Stein"],
                "description": "The comprehensive guide to algorithms with practical implementations.",
                "published_date": "2009-07-01",
                "isbn": "9780262033848",
                "url": "https://mitpress.mit.edu/9780262033848/introduction-to-algorithms/"
            },
            {
                "title": "Artificial Intelligence: A Modern Approach",
                "authors": ["Stuart Russell", "Peter Norvig"],
                "description": "The leading textbook in artificial intelligence, covering theory and practice.",
                "published_date": "2020-04-06",
                "isbn": "9780134610993",
                "url": "http://aima.cs.berkeley.edu/"
            }
        ]

        for book in popular_books:
            try:
                # 解析出版日期
                published_at = datetime.datetime.fromisoformat(book["published_date"])

                signal = self._create_signal_dict(
                    external_id=book["isbn"],
                    title=book["title"],
                    url=book["url"],
                    content=book["description"],
                    author=", ".join(book["authors"]),
                    published_at=published_at,
                    metadata_json=json.dumps({
                        "isbn": book["isbn"],
                        "authors": book["authors"],
                        "source": "curated_technical_books"
                    })
                )
                signals.append(signal)
            except Exception as e:
                print(f"Error processing book {book['title']}: {e}")
                continue

        return signals