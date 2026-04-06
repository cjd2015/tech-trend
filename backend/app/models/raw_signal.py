from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime

Base = declarative_base()

class RawSignal(Base):
    __tablename__ = 'raw_signals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(String(50), nullable=False)  # community, research, industry, knowledge
    source_name = Column(String(100), nullable=False)  # hacker_news, arxiv, patent, technical_book
    external_id = Column(String(255), nullable=False, unique=True)  # 外部系统ID
    title = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    content = Column(Text, nullable=True)  # 摘要或内容
    author = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=datetime.datetime.utcnow)
    metadata_json = Column(Text, nullable=True)  # 额外元数据JSON

    # 关联到主题证据
    topic_evidences = relationship("TopicEvidence", back_populates="raw_signal")

    def __repr__(self):
        return f"<RawSignal(id={self.id}, source_type={self.source_type}, title={self.title[:50]}...)>"

class Topic(Base):
    __tablename__ = 'topics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_name = Column(String(500), nullable=False)  # 规范化的主题名称
    aliases = Column(Text, nullable=True)  # JSON格式的别名列表
    keywords = Column(Text, nullable=True)  # JSON格式的关键字列表
    status = Column(String(50), nullable=False, default='observed')  # observed/candidate/validated/recorded/discarded
    first_seen_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.datetime.utcnow)

    # 评分字段
    community_score = Column(Float, default=0.0)
    research_score = Column(Float, default=0.0)
    industry_score = Column(Float, default=0.0)
    knowledge_score = Column(Float, default=0.0)
    cross_signal_score = Column(Float, default=0.0)
    novelty_score = Column(Float, default=0.0)
    momentum_score = Column(Float, default=0.0)
    final_score = Column(Float, default=0.0)

    # 关联
    topic_evidences = relationship("TopicEvidence", back_populates="topic")
    records = relationship("Record", back_populates="topic")

    def __repr__(self):
        return f"<Topic(id={self.id}, name={self.canonical_name}, status={self.status}, score={self.final_score})>"

class TopicEvidence(Base):
    __tablename__ = 'topic_evidences'

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey('topics.id'), nullable=False)
    raw_signal_id = Column(Integer, ForeignKey('raw_signals.id'), nullable=False)
    source_type = Column(String(50), nullable=False)
    weight = Column(Float, default=1.0)  # 证据权重
    matched_by = Column(String(100), nullable=True)  # 匹配方式：keyword/semantic/rule
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # 关联
    topic = relationship("Topic", back_populates="topic_evidences")
    raw_signal = relationship("RawSignal", back_populates="topic_evidences")

    def __repr__(self):
        return f"<TopicEvidence(topic_id={self.topic_id}, signal_id={self.raw_signal_id}, weight={self.weight})>"

class Record(Base):
    __tablename__ = 'records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey('topics.id'), nullable=False)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    record_reason = Column(Text, nullable=True)  # 记录理由说明
    evidence_count = Column(Integer, default=0)
    confidence = Column(Float, default=0.0)  # 置信度 0-1
    review_status = Column(String(50), default='useful')  # useful/approved/auto_approved (legacy statuses may remain)
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow)

    # 关联
    topic = relationship("Topic", back_populates="records")

    def __repr__(self):
        return f"<Record(id={self.id}, title={self.title}, status={self.review_status})>"
