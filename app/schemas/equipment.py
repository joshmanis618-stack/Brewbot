from pydantic import BaseModel
from typing import Optional


class EquipmentBase(BaseModel):
    name: str
    batch_size_l: float
    boil_size_l: float
    boil_time_min: int = 60
    efficiency: float = 75.0
    hop_utilization: float = 100.0
    trub_chiller_loss_l: float = 1.0
    lauter_deadspace_l: float = 0.0
    top_up_water_l: float = 0.0
    notes: Optional[str] = None


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(EquipmentBase):
    name: Optional[str] = None
    batch_size_l: Optional[float] = None
    boil_size_l: Optional[float] = None


class EquipmentRead(EquipmentBase):
    id: int

    model_config = {"from_attributes": True}
