from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
from .style import StyleRead
from .equipment import EquipmentRead
from .ingredients import FermentableRead, HopRead, YeastRead, MiscRead


class RecipeFermentableIn(BaseModel):
    fermentable_id: int
    amount_kg: float
    add_after_boil: bool = False


class RecipeFermentableRead(BaseModel):
    id: int
    fermentable_id: int
    amount_kg: float
    add_after_boil: bool
    fermentable: FermentableRead

    model_config = {"from_attributes": True}


class RecipeHopIn(BaseModel):
    hop_id: int
    amount_g: float
    time_min: int = 60
    use: str = "Boil"
    form: str = "Pellet"


class RecipeHopRead(BaseModel):
    id: int
    hop_id: int
    amount_g: float
    time_min: int
    use: str
    form: str
    hop: HopRead

    model_config = {"from_attributes": True}


class RecipeYeastIn(BaseModel):
    yeast_id: int
    amount: float = 1.0
    add_to_secondary: bool = False


class RecipeYeastRead(BaseModel):
    id: int
    yeast_id: int
    amount: float
    add_to_secondary: bool
    yeast: YeastRead

    model_config = {"from_attributes": True}


class RecipeMiscIn(BaseModel):
    misc_id: int
    amount: float
    amount_is_weight: bool = True
    time_min: int = 0
    use: str = "Boil"


class RecipeMiscRead(BaseModel):
    id: int
    misc_id: int
    amount: float
    amount_is_weight: bool
    time_min: int
    use: str
    misc: MiscRead

    model_config = {"from_attributes": True}


class RecipeBase(BaseModel):
    name: str
    type: str = "All Grain"
    style_id: Optional[int] = None
    equipment_id: Optional[int] = None
    batch_size_l: float
    boil_size_l: Optional[float] = None
    boil_time_min: int = 60
    efficiency: float = 75.0
    og: Optional[float] = None
    fg: Optional[float] = None
    abv: Optional[float] = None
    ibu: Optional[float] = None
    color_srm: Optional[float] = None
    notes: Optional[str] = None
    brewer: Optional[str] = None


class RecipeCreate(RecipeBase):
    fermentables: List[RecipeFermentableIn] = []
    hops: List[RecipeHopIn] = []
    yeasts: List[RecipeYeastIn] = []
    miscs: List[RecipeMiscIn] = []


class RecipeUpdate(RecipeBase):
    name: Optional[str] = None
    batch_size_l: Optional[float] = None
    fermentables: Optional[List[RecipeFermentableIn]] = None
    hops: Optional[List[RecipeHopIn]] = None
    yeasts: Optional[List[RecipeYeastIn]] = None
    miscs: Optional[List[RecipeMiscIn]] = None


class RecipeRead(RecipeBase):
    id: int
    version: int
    created_at: datetime
    updated_at: datetime
    style: Optional[StyleRead] = None
    equipment: Optional[EquipmentRead] = None
    fermentables: List[RecipeFermentableRead] = []
    hops: List[RecipeHopRead] = []
    yeasts: List[RecipeYeastRead] = []
    miscs: List[RecipeMiscRead] = []

    model_config = {"from_attributes": True}


class RecipeSummary(BaseModel):
    id: int
    name: str
    type: str
    batch_size_l: float
    og: Optional[float] = None
    abv: Optional[float] = None
    ibu: Optional[float] = None
    color_srm: Optional[float] = None
    brewer: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
