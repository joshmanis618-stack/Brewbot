from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Any


class RigProfileBase(BaseModel):
    name: str
    type: str = "custom"
    description: Optional[str] = None


class RigProfileCreate(RigProfileBase):
    pass


class RigProfileUpdate(RigProfileBase):
    name: Optional[str] = None


class RigProfileRead(RigProfileBase):
    id: int

    model_config = {"from_attributes": True}


class DeviceBase(BaseModel):
    name: str
    device_key: str
    type: str
    role: Optional[str] = None
    protocol: str = "mqtt"
    config: Optional[dict] = None
    rig_id: Optional[int] = None


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(DeviceBase):
    name: Optional[str] = None
    device_key: Optional[str] = None
    type: Optional[str] = None


class DeviceRead(DeviceBase):
    id: int
    is_online: bool
    last_seen: Optional[datetime] = None
    current_value: Optional[float] = None
    current_unit: Optional[str] = None

    model_config = {"from_attributes": True}


class DeviceReadingRead(BaseModel):
    id: int
    device_id: int
    value: float
    unit: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class DeviceCommand(BaseModel):
    action: str                   # "on" | "off" | "set"
    value: Optional[float] = None # used with "set" (e.g. PID setpoint)
