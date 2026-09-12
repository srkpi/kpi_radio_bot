from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AlertLevelEntry(BaseModel):
    alert_level: Optional[str] = Field(None, alias="alertLevel")
    reason: Optional[str] = None
    created_at: Optional[datetime] = Field(None, alias="createdAt")


class RegionAlerts(BaseModel):
    status: str
    region_id: int = Field(..., alias="regionId")
    alarm_type: str = Field(..., alias="alarmType")
    created_at: datetime = Field(..., alias="createdAt")
    alert_level: Optional[str] = Field(None, alias="alertLevel")
    reason: Optional[str] = None
    active_alert_levels: Optional[list[AlertLevelEntry]] = Field(
        None, alias="activeAlertLevels"
    )
