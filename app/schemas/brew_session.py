from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class BrewSessionBase(BaseModel):
    recipe_id: int
    equipment_id: Optional[int] = None
    status: str = "planned"
    brew_date: Optional[datetime] = None
    package_date: Optional[datetime] = None
    actual_og: Optional[float] = None
    actual_fg: Optional[float] = None
    actual_abv: Optional[float] = None
    actual_batch_size_l: Optional[float] = None
    actual_efficiency: Optional[float] = None
    ferment_temp_c: Optional[float] = None
    notes: Optional[str] = None


class BrewSessionCreate(BrewSessionBase):
    pass


class BrewSessionUpdate(BrewSessionBase):
    recipe_id: Optional[int] = None
    status: Optional[str] = None


class BrewSessionRead(BrewSessionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
