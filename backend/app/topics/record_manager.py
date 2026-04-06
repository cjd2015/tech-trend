from datetime import datetime, timedelta
import json
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.models.raw_signal import Record, Topic
from app.topics.reviewer import TopicAutoReviewer


class RecordManager:
    """记录管理器：管理记录的创建、审核和查询。"""

    VALID_STATUSES = {"useful", "approved", "auto_approved", "pending_review", "rejected"}
    STORED_STATUSES = {"useful", "approved", "auto_approved"}

    def __init__(self, db: Session):
        self.db = db
        self.reviewer = TopicAutoReviewer(db)

    def get_records(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Record]:
        """获取记录列表。"""
        query = self.db.query(Record).join(Topic)
        query = self._apply_status_filter(query, status)

        return (
            query.order_by(desc(Record.recorded_at))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_record_by_id(self, record_id: int) -> Optional[Record]:
        """根据 ID 获取记录。"""
        return self.db.query(Record).filter(Record.id == record_id).first()

    def get_records_by_topic(self, topic_id: int) -> List[Record]:
        """获取主题相关的所有记录。"""
        return (
            self.db.query(Record)
            .filter(Record.topic_id == topic_id)
            .order_by(desc(Record.recorded_at))
            .all()
        )

    def create_record_for_topic(
        self,
        topic_id: int,
    ) -> Optional[Record]:
        """对指定主题执行自动审核，只有 useful 结果才会入库。"""

        topic = self.db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            return None

        report = self.reviewer.review_topic(topic)
        self.reviewer.apply_review(topic, report)
        self.db.commit()

        if not report["store"]:
            return None

        record = self.db.query(Record).filter(Record.topic_id == topic_id).first()
        if record:
            self.db.refresh(record)
        return record

    def update_record_status(self, record_id: int, new_status: str) -> Optional[Record]:
        """更新记录审核状态。保留兼容旧接口，不作为主流程使用。"""
        if new_status not in self.VALID_STATUSES:
            return None

        record = self.get_record_by_id(record_id)
        if not record:
            return None

        record.review_status = new_status
        if new_status in self.STORED_STATUSES and record.topic:
            record.topic.status = "recorded"
        elif record.topic:
            record.topic.status = "discarded"

        self.db.commit()
        self.db.refresh(record)
        return record

    def update_record_content(self, record_id: int, updates: Dict[str, Any]) -> Optional[Record]:
        """更新记录内容。"""
        record = self.get_record_by_id(record_id)
        if not record:
            return None

        for field in ("title", "summary", "record_reason"):
            if field in updates:
                setattr(record, field, updates[field])

        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_record(self, record_id: int) -> bool:
        """删除记录。仅保留兼容旧接口。"""
        record = self.get_record_by_id(record_id)
        if not record:
            return False

        if record.review_status in self.STORED_STATUSES:
            return False

        self.db.delete(record)
        self.db.commit()
        return True

    def get_record_statistics(self) -> Dict[str, Any]:
        """获取记录统计信息。"""
        total_records = self.db.query(Record).count()

        status_counts = {
            status: self.db.query(Record).filter(Record.review_status == status).count()
            for status in sorted(self.VALID_STATUSES)
        }

        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_records = (
            self.db.query(Record)
            .filter(Record.recorded_at >= week_ago)
            .count()
        )

        dimension_stats: Dict[str, int] = {}
        for record in self.db.query(Record).all():
            if not record.topic:
                continue
            for evidence in record.topic.topic_evidences:
                source_type = evidence.source_type
                dimension_stats[source_type] = dimension_stats.get(source_type, 0) + 1

        return {
            "total_records": total_records,
            "status_counts": status_counts,
            "recent_records": recent_records,
            "dimension_stats": dimension_stats,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """兼容旧调用的统计入口。"""
        return self.get_record_statistics()

    def search_records(
        self,
        query: str,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> List[Record]:
        """搜索记录。"""
        search_filter = or_(
            Record.title.ilike(f"%{query}%"),
            Record.summary.ilike(f"%{query}%"),
            Record.record_reason.ilike(f"%{query}%"),
            Topic.canonical_name.ilike(f"%{query}%"),
        )

        records = self.db.query(Record).join(Topic).filter(search_filter)
        records = self._apply_status_filter(records, status)

        return records.order_by(desc(Record.recorded_at)).limit(limit).all()

    def bulk_update_status(self, record_ids: List[int], new_status: str) -> Dict[str, int]:
        """批量更新记录状态。"""
        updated = 0
        failed = 0

        for record_id in record_ids:
            if self.update_record_status(record_id, new_status):
                updated += 1
            else:
                failed += 1

        return {"updated": updated, "failed": failed}

    def export_records(self, status: Optional[str] = "stored", format: str = "json") -> str:
        """导出记录。"""
        records = self.get_records(status=status, limit=10000, offset=0)

        if format != "json":
            return "Unsupported format"

        export_data = []
        for record in records:
            export_data.append(
                {
                    "id": record.id,
                    "title": record.title,
                    "summary": record.summary,
                    "record_reason": record.record_reason,
                    "confidence": record.confidence,
                    "review_status": record.review_status,
                    "recorded_at": record.recorded_at.isoformat() if record.recorded_at else None,
                    "topic": {
                        "id": record.topic.id if record.topic else None,
                        "canonical_name": record.topic.canonical_name if record.topic else None,
                        "final_score": record.topic.final_score if record.topic else None,
                    },
                    "evidence_count": len(record.topic.topic_evidences) if record.topic else 0,
                }
            )

        return json.dumps(export_data, ensure_ascii=False, indent=2)

    def _generate_summary(self, topic: Topic) -> str:
        """为记录生成简短摘要。"""
        dimension_counts: Dict[str, int] = {}
        for evidence in topic.topic_evidences:
            dimension_counts[evidence.source_type] = dimension_counts.get(evidence.source_type, 0) + 1

        if not dimension_counts:
            return "当前主题尚未关联有效证据。"

        parts = []
        labels = {
            "community": "社区",
            "research": "研究",
            "industry": "产业",
            "knowledge": "知识",
        }
        for key, count in sorted(dimension_counts.items()):
            parts.append(f"{labels.get(key, key)}证据 {count} 条")

        return f"主题已聚合 {len(topic.topic_evidences)} 条证据，覆盖 {len(dimension_counts)} 个维度：{'，'.join(parts)}。"

    def _generate_record_reason(self, topic: Topic) -> str:
        """为记录生成说明。"""
        reasons = []

        score_map = {
            "community_score": "社区热度",
            "research_score": "研究关注",
            "industry_score": "产业投入",
            "knowledge_score": "知识沉淀",
        }
        for field, label in score_map.items():
            value = getattr(topic, field, 0.0) or 0.0
            if value > 0:
                reasons.append(f"{label} {value:.1f}")

        if (topic.cross_signal_score or 0.0) > 0:
            reasons.append(f"交叉信号 {topic.cross_signal_score:.1f}")

        if not reasons:
            reasons.append("达到记录阈值")

        return "；".join(reasons)

    def _apply_status_filter(self, query, status: Optional[str]):
        if status in {None, "", "stored"}:
            return query.filter(Record.review_status.in_(self.STORED_STATUSES))
        if status == "all":
            return query
        return query.filter(Record.review_status == status)
