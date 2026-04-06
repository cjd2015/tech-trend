from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class RawSignalBase(BaseModel):
    source_type: str
    source_name: str
    external_id: str
    title: Optional[str] = None
    url: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    metadata_json: Optional[str] = None

class RawSignalCreate(RawSignalBase):
    pass

class RawSignal(RawSignalBase):
    id: int
    fetched_at: datetime

    class Config:
        from_attributes = True