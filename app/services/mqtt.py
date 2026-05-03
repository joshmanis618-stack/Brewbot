"""
MQTT service — bridges hardware devices to the Brewbot server.

Topic schema
------------
brewbot/register                  device → server  (announce on connect)
brewbot/{device_key}/reading      device → server  (sensor value)
brewbot/{device_key}/state        device → server  (online/offline)
brewbot/{device_key}/command      server → device  (on/off/set)

Register payload:
    {"device_key": "hlt_temp", "name": "HLT Temp", "type": "temperature_sensor"}

Reading payload:
    {"value": 65.2, "unit": "C"}

State payload:
    {"online": true}

Command payload:
    {"action": "on"}
    {"action": "set", "value": 75.0}
"""

import asyncio
import json
import logging
import os
from datetime import datetime

import aiomqtt

from app.database import SessionLocal
from app.models.device import Device, DeviceReading
from app.services.ws_manager import ws_manager

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

logger = logging.getLogger(__name__)

# Holds the active client so routes can publish commands
_client: aiomqtt.Client | None = None


async def publish(topic: str, payload: dict) -> bool:
    """Publish a message. Returns False if broker not connected."""
    if _client is None:
        logger.warning("MQTT publish attempted but client not connected")
        return False
    await _client.publish(topic, json.dumps(payload))
    return True


# ── message handlers ─────────────────────────────────────────────────────────

async def _handle_register(payload: dict) -> None:
    device_key = payload.get("device_key")
    if not device_key:
        return
    db = SessionLocal()
    try:
        device = db.query(Device).filter_by(device_key=device_key).first()
        if not device:
            device = Device(
                device_key=device_key,
                name=payload.get("name", device_key),
                type=payload.get("type", "unknown"),
            )
            db.add(device)
            logger.info("Auto-registered new device: %s", device_key)
        device.is_online = True
        device.last_seen = datetime.utcnow()
        db.commit()
    finally:
        db.close()

    await ws_manager.broadcast({"type": "device_registered", "device_key": device_key})


async def _handle_reading(device_key: str, payload: dict) -> None:
    value = payload.get("value")
    if value is None:
        return
    unit = payload.get("unit", "C")

    db = SessionLocal()
    try:
        device = db.query(Device).filter_by(device_key=device_key).first()
        if not device:
            return
        db.add(DeviceReading(device_id=device.id, value=value, unit=unit))
        device.current_value = value
        device.current_unit = unit
        device.last_seen = datetime.utcnow()
        device.is_online = True
        db.commit()
        device_name = device.name
    finally:
        db.close()

    await ws_manager.broadcast({
        "type": "reading",
        "device_key": device_key,
        "device_name": device_name,
        "value": value,
        "unit": unit,
        "timestamp": datetime.utcnow().isoformat(),
    })


async def _handle_state(device_key: str, payload: dict) -> None:
    online = payload.get("online", False)
    db = SessionLocal()
    try:
        device = db.query(Device).filter_by(device_key=device_key).first()
        if not device:
            return
        device.is_online = online
        if online:
            device.last_seen = datetime.utcnow()
        db.commit()
    finally:
        db.close()

    await ws_manager.broadcast({
        "type": "state",
        "device_key": device_key,
        "online": online,
    })


async def _dispatch(message: aiomqtt.Message) -> None:
    topic = str(message.topic)
    try:
        payload = json.loads(message.payload)
    except (json.JSONDecodeError, TypeError):
        return

    parts = topic.split("/")
    if topic == "brewbot/register":
        await _handle_register(payload)
    elif len(parts) == 3 and parts[0] == "brewbot":
        _, device_key, event = parts
        if event == "reading":
            await _handle_reading(device_key, payload)
        elif event == "state":
            await _handle_state(device_key, payload)


# ── main loop ─────────────────────────────────────────────────────────────────

async def run() -> None:
    """Persistent MQTT listener with automatic reconnect."""
    global _client
    while True:
        try:
            async with aiomqtt.Client(MQTT_HOST, MQTT_PORT) as client:
                _client = client
                await client.subscribe("brewbot/#")
                logger.info("MQTT connected to %s:%s", MQTT_HOST, MQTT_PORT)
                async for message in client.messages:
                    asyncio.create_task(_dispatch(message))
        except aiomqtt.MqttError as exc:
            _client = None
            logger.warning("MQTT disconnected (%s) — retrying in 5 s", exc)
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            _client = None
            raise
