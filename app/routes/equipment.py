from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.equipment import Equipment
from app.schemas.equipment import EquipmentCreate, EquipmentUpdate, EquipmentRead

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.get("/", response_model=List[EquipmentRead])
def list_equipment(db: Session = Depends(get_db)):
    return db.query(Equipment).all()


@router.post("/", response_model=EquipmentRead, status_code=201)
def create_equipment(payload: EquipmentCreate, db: Session = Depends(get_db)):
    item = Equipment(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{equipment_id}", response_model=EquipmentRead)
def get_equipment(equipment_id: int, db: Session = Depends(get_db)):
    item = db.get(Equipment, equipment_id)
    if not item:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return item


@router.put("/{equipment_id}", response_model=EquipmentRead)
def update_equipment(equipment_id: int, payload: EquipmentUpdate, db: Session = Depends(get_db)):
    item = db.get(Equipment, equipment_id)
    if not item:
        raise HTTPException(status_code=404, detail="Equipment not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{equipment_id}", status_code=204)
def delete_equipment(equipment_id: int, db: Session = Depends(get_db)):
    item = db.get(Equipment, equipment_id)
    if not item:
        raise HTTPException(status_code=404, detail="Equipment not found")
    db.delete(item)
    db.commit()
