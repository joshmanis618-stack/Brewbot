from pydantic import BaseModel
from typing import Optional


# --- Fermentable ---

class FermentableBase(BaseModel):
    name: str
    type: str
    origin: Optional[str] = None
    supplier: Optional[str] = None
    color_srm: float = 0.0
    potential: float = 1.037
    yield_pct: float = 75.0
    moisture_pct: float = 4.0
    diastatic_power: float = 0.0
    protein_pct: Optional[float] = None
    max_in_batch_pct: Optional[float] = None
    add_after_boil: bool = False
    recommend_mash: bool = True
    notes: Optional[str] = None


class FermentableCreate(FermentableBase):
    pass


class FermentableUpdate(FermentableBase):
    name: Optional[str] = None
    type: Optional[str] = None


class FermentableRead(FermentableBase):
    id: int

    model_config = {"from_attributes": True}


# --- Hop ---

class HopBase(BaseModel):
    name: str
    origin: Optional[str] = None
    type: Optional[str] = None
    alpha_pct: float
    beta_pct: Optional[float] = None
    hsi: Optional[float] = None
    caryophyllene_pct: Optional[float] = None
    cohumulone_pct: Optional[float] = None
    myrcene_pct: Optional[float] = None
    humulene_pct: Optional[float] = None
    notes: Optional[str] = None
    substitutes: Optional[str] = None


class HopCreate(HopBase):
    pass


class HopUpdate(HopBase):
    name: Optional[str] = None
    alpha_pct: Optional[float] = None


class HopRead(HopBase):
    id: int

    model_config = {"from_attributes": True}


# --- Yeast ---

class YeastBase(BaseModel):
    name: str
    lab: Optional[str] = None
    product_id: Optional[str] = None
    type: Optional[str] = None
    form: Optional[str] = None
    min_temp_c: Optional[float] = None
    max_temp_c: Optional[float] = None
    attenuation_pct: float = 75.0
    flocculation: Optional[str] = None
    best_for: Optional[str] = None
    notes: Optional[str] = None


class YeastCreate(YeastBase):
    pass


class YeastUpdate(YeastBase):
    name: Optional[str] = None


class YeastRead(YeastBase):
    id: int

    model_config = {"from_attributes": True}


# --- Misc ---

class MiscBase(BaseModel):
    name: str
    type: Optional[str] = None
    use_for: Optional[str] = None
    notes: Optional[str] = None


class MiscCreate(MiscBase):
    pass


class MiscUpdate(MiscBase):
    name: Optional[str] = None


class MiscRead(MiscBase):
    id: int

    model_config = {"from_attributes": True}
