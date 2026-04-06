from sqlalchemy.orm import Session
from app.services.signal_service import SignalService
from app.collectors import get_collector, list_collectors
from app.schemas.raw_signal import RawSignalCreate
import asyncio

class CollectionService:
    """采集服务"""

    def __init__(self, db: Session):
        self.db = db
        self.signal_service = SignalService(db)

    async def collect_from_source(self, collector_name: str) -> int:
        """从指定采集器收集信号"""
        normalized_name = collector_name
        if '/' in normalized_name:
            normalized_name = normalized_name.split('/')[-1]

        if normalized_name not in list_collectors():
            raise ValueError(f"Unknown collector: {collector_name}")

        collector = get_collector(normalized_name)
        signals_data = await collector.collect()

        collected_count = 0
        for signal_data in signals_data:
            # 检查是否已存在
            existing = self.signal_service.get_signal_by_external_id(signal_data["external_id"])
            if not existing:
                signal_create = RawSignalCreate(**signal_data)
                self.signal_service.create_signal(signal_create)
                collected_count += 1

        return collected_count

    async def collect_all(self) -> dict:
        """收集所有来源的信号"""
        results = {}
        collector_names = list_collectors()
        tasks = [get_collector(name).collect() for name in collector_names]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for collector_name, outcome in zip(collector_names, completed):
            if isinstance(outcome, Exception):
                results[collector_name] = f"Error: {str(outcome)}"
                continue

            collected_count = 0
            for signal_data in outcome:
                existing = self.signal_service.get_signal_by_external_id(signal_data["external_id"])
                if not existing:
                    signal_create = RawSignalCreate(**signal_data)
                    self.signal_service.create_signal(signal_create)
                    collected_count += 1

            results[collector_name] = collected_count

        return results