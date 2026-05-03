from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.brew_session import BrewSession
from app.schemas.brew_session import BrewSessionCreate, BrewSessionUpdate, BrewSessionRead

router = APIRouter(prefix="/brew-sessions", tags=["brew-sessions"])


@router.get("/", response_model=List[BrewSessionRead])
def list_sessions(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(BrewSession).offset(skip).limit(limit).all()


@router.post("/", response_model=BrewSessionRead, status_code=201)
def create_session(payload: BrewSessionCreate, db: Session = Depends(get_db)):
    session = BrewSession(**payload.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=BrewSessionRead)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.get(BrewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Brew session not found")
    return session


@router.put("/{session_id}", response_model=BrewSessionRead)
def update_session(session_id: int, payload: BrewSessionUpdate, db: Session = Depends(get_db)):
    session = db.get(BrewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Brew session not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(session, field, value)
    db.commit()
    db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)):
    session = db.get(BrewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Brew session not found")
    db.delete(session)
    db.commit()
