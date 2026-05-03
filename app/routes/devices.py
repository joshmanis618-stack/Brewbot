from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.device import Device, DeviceReading, RigProfile
from app.schemas.device import (
    DeviceCreate, DeviceUpdate, DeviceRead, DeviceReadingRead, DeviceCommand,
    RigProfileCreate, RigProfileUpdate, RigProfileRead,
)
from app.services import mqtt
from app.services.ws_manager import ws_manager

router = APIRouter()


# ── Rig profiles ──────────────────────────────────────────────────────────────

@router.get("/rigs", response_model=List[RigProfileRead], tags=["rigs"])
def list_rigs(db: Session = Depends(get_db)):
    return db.query(RigProfile).all()


@router.post("/rigs", response_model=RigProfileRead, status_code=201, tags=["rigs"])
def create_rig(payload: RigProfileCreate, db: Session = Depends(get_db)):
    rig = RigProfile(**payload.model_dump())
    db.add(rig)
    db.commit()
    db.refresh(rig)
    return rig


@router.get("/rigs/{rig_id}", response_model=RigProfileRead, tags=["rigs"])
def get_rig(rig_id: int, db: Session = Depends(get_db)):
    rig = db.get(RigProfile, rig_id)
    if not rig:
        raise HTTPException(status_code=404, detail="Rig not found")
    return rig


@router.put("/rigs/{rig_id}", response_model=RigProfileRead, tags=["rigs"])
def update_rig(rig_id: int, payload: RigProfileUpdate, db: Session = Depends(get_db)):
    rig = db.get(RigProfile, rig_id)
    if not rig:
        raise HTTPException(status_code=404, detail="Rig not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rig, field, value)
    db.commit()
    db.refresh(rig)
    return rig


@router.delete("/rigs/{rig_id}", status_code=204, tags=["rigs"])
def delete_rig(rig_id: int, db: Session = Depends(get_db)):
    rig = db.get(RigProfile, rig_id)
    if not rig:
        raise HTTPException(status_code=404, detail="Rig not found")
    db.delete(rig)
    db.commit()


# ── Devices ───────────────────────────────────────────────────────────────────

@router.get("/devices", response_model=List[DeviceRead], tags=["devices"])
def list_devices(db: Session = Depends(get_db)):
    return db.query(Device).all()


@router.post("/devices", response_model=DeviceRead, status_code=201, tags=["devices"])
def create_device(payload: DeviceCreate, db: Session = Depends(get_db)):
    device = Device(**payload.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.get("/devices/{device_id}", response_model=DeviceRead, tags=["devices"])
def get_device(device_id: int, db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.put("/devices/{device_id}", response_model=DeviceRead, tags=["devices"])
def update_device(device_id: int, payload: DeviceUpdate, db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(device, field, value)
    db.commit()
    db.refresh(device)
    return device


@router.delete("/devices/{device_id}", status_code=204, tags=["devices"])
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(device)
    db.commit()


@router.get("/devices/{device_id}/readings", response_model=List[DeviceReadingRead], tags=["devices"])
def get_readings(device_id: int, limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(DeviceReading)
        .filter(DeviceReading.device_id == device_id)
        .order_by(DeviceReading.timestamp.desc())
        .limit(limit)
        .all()
    )


@router.post("/devices/{device_id}/command", tags=["devices"])
async def send_command(device_id: int, command: DeviceCommand, db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    sent = await mqtt.publish(
        f"brewbot/{device.device_key}/command",
        command.model_dump(exclude_none=True),
    )
    if not sent:
        raise HTTPException(status_code=503, detail="MQTT broker not connected")
    return {"status": "sent", "device_key": device.device_key}


# ── WebSocket live feed ───────────────────────────────────────────────────────

@router.websocket("/ws/readings")
async def readings_ws(websocket: WebSocket):
    """
    Connect to receive live device readings and state changes as JSON.
    The server also accepts any text to keep the connection alive (ping).
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
