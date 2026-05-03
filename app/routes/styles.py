from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.style import Style
from app.schemas.style import StyleCreate, StyleUpdate, StyleRead

router = APIRouter(prefix="/styles", tags=["styles"])


@router.get("/", response_model=List[StyleRead])
def list_styles(db: Session = Depends(get_db)):
    return db.query(Style).all()


@router.post("/", response_model=StyleRead, status_code=201)
def create_style(payload: StyleCreate, db: Session = Depends(get_db)):
    style = Style(**payload.model_dump())
    db.add(style)
    db.commit()
    db.refresh(style)
    return style


@router.get("/{style_id}", response_model=StyleRead)
def get_style(style_id: int, db: Session = Depends(get_db)):
    style = db.get(Style, style_id)
    if not style:
        raise HTTPException(status_code=404, detail="Style not found")
    return style


@router.put("/{style_id}", response_model=StyleRead)
def update_style(style_id: int, payload: StyleUpdate, db: Session = Depends(get_db)):
    style = db.get(Style, style_id)
    if not style:
        raise HTTPException(status_code=404, detail="Style not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(style, field, value)
    db.commit()
    db.refresh(style)
    return style


@router.delete("/{style_id}", status_code=204)
def delete_style(style_id: int, db: Session = Depends(get_db)):
    style = db.get(Style, style_id)
    if not style:
        raise HTTPException(status_code=404, detail="Style not found")
    db.delete(style)
    db.commit()
