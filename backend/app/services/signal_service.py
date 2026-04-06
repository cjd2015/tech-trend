from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.raw_signal import RawSignal
from app.schemas.raw_signal import RawSignalCreate
from typing import List, Optional, Dict, Any

class SignalService:
    """信号服务层"""

    def __init__(self, db: Session):
        self.db = db

    def create_signal(self, signal: RawSignalCreate) -> RawSignal:
        """创建新信号"""
        db_signal = RawSignal(**signal.model_dump())
        self.db.add(db_signal)
        self.db.commit()
        self.db.refresh(db_signal)
        return db_signal

    def get_signals(self, skip: int = 0, limit: int = 100, source_type: Optional[str] = None, source_name: Optional[str] = None) -> List[RawSignal]:
        """获取信号列表"""
        query = self.db.query(RawSignal)
        if source_type:
            query = query.filter(RawSignal.source_type == source_type)
        if source_name:
            query = query.filter(RawSignal.source_name == source_name)
        return query.offset(skip).limit(limit).all()

    def get_signals_by_source(self, source_type: str, source_name: str) -> List[RawSignal]:
        """按来源获取信号"""
        return self.db.query(RawSignal).filter(
            RawSignal.source_type == source_type,
            RawSignal.source_name == source_name
        ).all()

    def get_source_counts(self) -> List[Dict[str, Any]]:
        """按来源统计信号数量"""
        results = self.db.query(
            RawSignal.source_type,
            RawSignal.source_name,
            func.count(RawSignal.id).label("count")
        ).group_by(RawSignal.source_type, RawSignal.source_name).all()

        return [
            {
                "source_type": source_type,
                "source_name": source_name,
                "count": count
            }
            for source_type, source_name, count in results
        ]

    def get_signal_by_external_id(self, external_id: str) -> RawSignal:
        """按外部ID获取信号"""
        return self.db.query(RawSignal).filter(RawSignal.external_id == external_id).first()