from datetime import datetime

from pydantic import BaseModel, Field


class RegionAlerts(BaseModel):
    status: str
    region_id: int = Field(..., alias="regionId")
    alarm_type: str = Field(..., alias="alarmType")
    created_at: datetime = Field(..., alias="createdAt")
