from pydantic import BaseModel
from typing import Optional


class StyleBase(BaseModel):
    name: str
    category: Optional[str] = None
    style_guide: Optional[str] = None
    style_letter: Optional[str] = None
    type: Optional[str] = None
    og_min: Optional[float] = None
    og_max: Optional[float] = None
    fg_min: Optional[float] = None
    fg_max: Optional[float] = None
    ibu_min: Optional[float] = None
    ibu_max: Optional[float] = None
    color_min: Optional[float] = None
    color_max: Optional[float] = None
    abv_min: Optional[float] = None
    abv_max: Optional[float] = None
    carb_min: Optional[float] = None
    carb_max: Optional[float] = None
    notes: Optional[str] = None
    profile: Optional[str] = None
    ingredients: Optional[str] = None
    examples: Optional[str] = None


class StyleCreate(StyleBase):
    pass


class StyleUpdate(StyleBase):
    name: Optional[str] = None


class StyleRead(StyleBase):
    id: int

    model_config = {"from_attributes": True}
