import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.raw_signal import Record, Topic
from app.topics.aggregator import TopicAggregator
from app.topics.classifier import TopicClassifier
from app.topics.record_manager import RecordManager
from app.topics.reviewer import TopicAutoReviewer
from app.topics.scorer import TopicScorer

router = APIRouter(prefix="/topics", tags=["topics"])


class ClassificationResult(BaseModel):
    promoted_to_candidate: int
    promoted_to_validated: int
    promoted_to_recorded: int
    demoted: int
    reviewed: int
    useful: int
    reference: int
    discarded: int
    stored: int
    removed: int


class RecordStatusUpdate(BaseModel):
    status: str


class RecordContentUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    record_reason: Optional[str] = None


def _parse_json_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    try:
        loaded = json.loads(value)
        if isinstance(loaded, list):
            return [str(item) for item in loaded]
    except json.JSONDecodeError:
        return []
    return []


def _to_iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _model_to_dict(payload: BaseModel) -> Dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_none=True)
    return payload.dict(exclude_none=True)


def _serialize_record(record: Record) -> Dict[str, Any]:
    return {
        "id": record.id,
        "topic_id": record.topic_id,
        "topic_name": record.topic.canonical_name if record.topic else None,
        "topic_status": record.topic.status if record.topic else None,
        "topic_score": record.topic.final_score if record.topic else None,
        "title": record.title,
        "summary": record.summary,
        "record_reason": record.record_reason,
        "confidence": record.confidence,
        "review_status": record.review_status,
        "evidence_count": record.evidence_count,
        "recorded_at": _to_iso(record.recorded_at),
    }


def _serialize_evidence(evidence) -> Dict[str, Any]:
    signal = evidence.raw_signal
    return {
        "id": evidence.id,
        "source_type": evidence.source_type,
        "weight": evidence.weight,
        "matched_by": evidence.matched_by,
        "created_at": _to_iso(evidence.created_at),
        "signal": {
            "id": signal.id,
            "source_type": signal.source_type,
            "source_name": signal.source_name,
            "title": signal.title,
            "content": signal.content,
            "author": signal.author,
            "url": signal.url,
            "published_at": _to_iso(signal.published_at),
            "fetched_at": _to_iso(signal.fetched_at),
            "metadata_json": signal.metadata_json,
        },
    }


def _serialize_topic(
    topic: Topic,
    review: Optional[Dict[str, Any]] = None,
    include_evidence: bool = False,
    include_records: bool = False,
) -> Dict[str, Any]:
    source_types = sorted({evidence.source_type for evidence in topic.topic_evidences})
    payload = {
        "id": topic.id,
        "canonical_name": topic.canonical_name,
        "aliases": _parse_json_list(topic.aliases),
        "keywords": _parse_json_list(topic.keywords),
        "status": topic.status,
        "final_score": topic.final_score,
        "community_score": topic.community_score,
        "research_score": topic.research_score,
        "industry_score": topic.industry_score,
        "knowledge_score": topic.knowledge_score,
        "cross_signal_score": topic.cross_signal_score,
        "momentum_score": topic.momentum_score,
        "novelty_score": topic.novelty_score,
        "evidence_count": len(topic.topic_evidences),
        "source_types": source_types,
        "first_seen_at": _to_iso(topic.first_seen_at),
        "last_seen_at": _to_iso(topic.last_seen_at),
    }

    if review:
        payload["review"] = review
        payload["review_score"] = review["weighted_total"]
        payload["review_conclusion"] = review["conclusion"]

    if include_evidence:
        evidences = sorted(
            topic.topic_evidences,
            key=lambda item: item.raw_signal.published_at or item.raw_signal.fetched_at or item.created_at or datetime.min,
            reverse=True,
        )
        payload["evidences"] = [_serialize_evidence(evidence) for evidence in evidences]
        payload["timeline"] = [
            {
                "evidence_id": evidence.id,
                "source_type": evidence.source_type,
                "source_name": evidence.raw_signal.source_name,
                "title": evidence.raw_signal.title,
                "occurred_at": _to_iso(
                    evidence.raw_signal.published_at or evidence.raw_signal.fetched_at or evidence.created_at
                ),
            }
            for evidence in evidences
        ]

    if include_records:
        records = sorted(
            topic.records,
            key=lambda item: item.recorded_at or datetime.min,
            reverse=True,
        )
        payload["records"] = [_serialize_record(record) for record in records]

    return payload


@router.get("")
async def get_topics(
    status: Optional[str] = Query(None, description="Filter by status: observed, candidate, validated, recorded"),
    min_score: Optional[float] = Query(None, description="Minimum final score"),
    limit: int = Query(50, description="Maximum number of topics to return"),
    offset: int = Query(0, description="Number of topics to skip"),
    db: Session = Depends(get_db),
):
    """获取主题列表。"""
    query = db.query(Topic)
    reviewer = TopicAutoReviewer(db)

    if status:
        query = query.filter(Topic.status == status)

    if min_score is not None:
        query = query.filter(Topic.final_score >= min_score)

    topics = (
        query.order_by(Topic.final_score.desc(), Topic.last_seen_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [_serialize_topic(topic, review=reviewer.review_topic(topic)) for topic in topics]


@router.get("/statistics")
async def get_statistics(db: Session = Depends(get_db)):
    """获取主题和记录的汇总统计。"""
    manager = RecordManager(db)
    record_stats = manager.get_record_statistics()

    status_counts: Dict[str, int] = {}
    for topic in db.query(Topic).all():
        status_counts[topic.status] = status_counts.get(topic.status, 0) + 1

    return {
        "total_topics": sum(status_counts.values()),
        "topic_status_counts": status_counts,
        "records": record_stats,
    }


@router.get("/search")
async def search_topics(
    q: str = Query(..., description="Search query"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, description="Maximum number of results"),
    db: Session = Depends(get_db),
):
    """搜索记录。"""
    manager = RecordManager(db)
    records = manager.search_records(q, status, limit)
    return {
        "results": [_serialize_record(record) for record in records],
        "total": len(records),
    }


@router.post("/aggregate")
async def aggregate_topics(db: Session = Depends(get_db)):
    """执行主题聚合。"""
    aggregator = TopicAggregator(db)
    result = aggregator.aggregate_topics()
    return {
        "message": "Topic aggregation completed",
        "processed_signals": result["processed_signals"],
        "created_topics": result["created_topics"],
        "merged_topics": result["merged_topics"],
    }


@router.post("/score")
async def score_topics(db: Session = Depends(get_db)):
    """为主题计算评分。"""
    scorer = TopicScorer(db)
    result = scorer.update_topic_scores()
    return {
        "message": "Topic scoring completed",
        **result,
    }


@router.post("/classify", response_model=ClassificationResult)
async def classify_topics(db: Session = Depends(get_db)):
    """分类主题状态。"""
    classifier = TopicClassifier(db)
    result = classifier.classify_topics()
    return ClassificationResult(**result)


@router.post("/review")
async def review_topics(
    topic_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db),
):
    """执行自动审核，useful 结果直接入库，其他结果丢弃。"""
    reviewer = TopicAutoReviewer(db)
    result = reviewer.review_topics(topic_ids)
    return {
        "message": "Topic auto review completed",
        **result,
    }


@router.post("/pipeline")
async def run_topic_pipeline(db: Session = Depends(get_db)):
    """运行完整的主题处理管道。"""
    aggregator = TopicAggregator(db)
    aggregation = aggregator.aggregate_topics()

    scorer = TopicScorer(db)
    scoring = scorer.update_topic_scores()

    classifier = TopicClassifier(db)
    classification = classifier.classify_topics()

    return {
        "aggregation": aggregation,
        "scoring": scoring,
        "classification": classification,
    }


@router.get("/records")
async def get_records(
    status: Optional[str] = Query("stored", description="Filter by review status"),
    limit: int = Query(50, description="Maximum number of records to return"),
    offset: int = Query(0, description="Number of records to skip"),
    db: Session = Depends(get_db),
):
    """获取记录列表。"""
    manager = RecordManager(db)
    records = manager.get_records(status=status, limit=limit, offset=offset)
    return [_serialize_record(record) for record in records]


@router.get("/records/{record_id}")
async def get_record(record_id: int, db: Session = Depends(get_db)):
    """获取单个记录详情。"""
    manager = RecordManager(db)
    record = manager.get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return _serialize_record(record)


@router.put("/records/{record_id}")
async def update_record_content(
    record_id: int,
    payload: RecordContentUpdate,
    db: Session = Depends(get_db),
):
    """更新记录内容。"""
    manager = RecordManager(db)
    record = manager.update_record_content(
        record_id,
        _model_to_dict(payload),
    )

    if not record:
        raise HTTPException(status_code=400, detail="Failed to update record")

    return _serialize_record(record)


@router.post("/{topic_id}/review")
async def review_single_topic(topic_id: int, db: Session = Depends(get_db)):
    """对单个主题执行自动审核并按结果决定是否入库。"""
    manager = RecordManager(db)
    record = manager.create_record_for_topic(topic_id)
    reviewer = TopicAutoReviewer(db)
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    report = reviewer.review_topic(topic)
    return {
        "topic_id": topic_id,
        "stored": record is not None,
        "record": _serialize_record(record) if record else None,
        "review": report,
    }


@router.get("/{topic_id}/evidence")
async def get_topic_evidence(topic_id: int, db: Session = Depends(get_db)):
    """获取单个主题的证据列表。"""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return _serialize_topic(topic, include_evidence=True)["evidences"]


@router.get("/{topic_id}/timeline")
async def get_topic_timeline(topic_id: int, db: Session = Depends(get_db)):
    """获取单个主题的时间线。"""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return _serialize_topic(topic, include_evidence=True)["timeline"]


@router.get("/{topic_id}")
async def get_topic(topic_id: int, db: Session = Depends(get_db)):
    """获取单个主题详情。"""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    reviewer = TopicAutoReviewer(db)
    return _serialize_topic(
        topic,
        review=reviewer.review_topic(topic),
        include_evidence=True,
        include_records=True,
    )
