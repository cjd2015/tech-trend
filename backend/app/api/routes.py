from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.core.database import get_db
from app.services.signal_service import SignalService
from app.services.collection_service import CollectionService
from app.schemas.raw_signal import RawSignal
from app.api.topics import router as topics_router

router = APIRouter(prefix="/api")

# 包含topics路由
router.include_router(topics_router, prefix="")

@router.get("/status")
def api_status():
    return {"service": "tech-trend", "mode": "backend", "status": "ok"}

@router.get("/signals", response_model=List[RawSignal])
def get_signals(
    skip: int = 0,
    limit: int = 100,
    source_type: Optional[str] = None,
    source_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取信号列表，可按来源过滤"""
    service = SignalService(db)
    return service.get_signals(skip, limit, source_type, source_name)

@router.get("/sources")
def get_signal_sources(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """返回当前信号来源统计信息"""
    service = SignalService(db)
    return service.get_source_counts()

@router.get("/signals/{source_type}/{source_name}", response_model=List[RawSignal])
def get_signals_by_source(source_type: str, source_name: str, db: Session = Depends(get_db)):
    """按来源获取信号"""
    service = SignalService(db)
    return service.get_signals_by_source(source_type, source_name)

@router.post("/collect")
async def collect_signals(source: Optional[str] = None, db: Session = Depends(get_db)):
    """触发信号采集，可选择单源采集"""
    service = CollectionService(db)

    if source:
        try:
            collected_count = await service.collect_from_source(source)
            results = {source: collected_count}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        results = await service.collect_all()

    return {"message": "Collection completed", "results": results}
