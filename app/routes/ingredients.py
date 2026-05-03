from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.fermentable import Fermentable
from app.models.hop import Hop
from app.models.yeast import Yeast
from app.models.misc import Misc
from app.schemas.ingredients import (
    FermentableCreate, FermentableUpdate, FermentableRead,
    HopCreate, HopUpdate, HopRead,
    YeastCreate, YeastUpdate, YeastRead,
    MiscCreate, MiscUpdate, MiscRead,
)

router = APIRouter(tags=["ingredients"])


def _crud_router(prefix: str, Model, CreateSchema, UpdateSchema, ReadSchema):
    """Build standard CRUD routes for an ingredient library model."""
    sub = APIRouter(prefix=prefix)

    @sub.get("/", response_model=List[ReadSchema])
    def list_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
        return db.query(Model).offset(skip).limit(limit).all()

    @sub.post("/", response_model=ReadSchema, status_code=201)
    def create_item(payload: CreateSchema, db: Session = Depends(get_db)):
        item = Model(**payload.model_dump())
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @sub.get("/{item_id}", response_model=ReadSchema)
    def get_item(item_id: int, db: Session = Depends(get_db)):
        item = db.get(Model, item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"{Model.__name__} not found")
        return item

    @sub.put("/{item_id}", response_model=ReadSchema)
    def update_item(item_id: int, payload: UpdateSchema, db: Session = Depends(get_db)):
        item = db.get(Model, item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"{Model.__name__} not found")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        db.commit()
        db.refresh(item)
        return item

    @sub.delete("/{item_id}", status_code=204)
    def delete_item(item_id: int, db: Session = Depends(get_db)):
        item = db.get(Model, item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"{Model.__name__} not found")
        db.delete(item)
        db.commit()

    return sub


fermentables_router = _crud_router("/fermentables", Fermentable, FermentableCreate, FermentableUpdate, FermentableRead)
hops_router = _crud_router("/hops", Hop, HopCreate, HopUpdate, HopRead)
yeasts_router = _crud_router("/yeasts", Yeast, YeastCreate, YeastUpdate, YeastRead)
miscs_router = _crud_router("/miscs", Misc, MiscCreate, MiscUpdate, MiscRead)
