from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, DateTime, JSON, Index
from sqlalchemy.orm import relationship
from .base import Base


class RigProfile(Base):
    __tablename__ = "rig_profiles"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    # single_vessel | rims_2vessel | herms_3vessel | brewmagic_3vessel | custom
    type = Column(String(30), default="custom")
    description = Column(Text)

    devices = relationship("Device", back_populates="rig")


class Device(Base):
    """
    A physical sensor or actuator.
    device_key is the stable identifier used in MQTT topics:
        brewbot/{device_key}/reading
        brewbot/{device_key}/command
        brewbot/{device_key}/state
    """
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    device_key = Column(String(100), unique=True, nullable=False)

    # temperature_sensor | heater | pump | valve | flow_meter
    type = Column(String(30), nullable=False)

    # Role within a rig: hlt_temp | mlt_temp | bk_temp |
    #   hlt_heater | mlt_heater | bk_heater |
    #   transfer_pump | recirc_pump |
    #   hlt_valve | mlt_valve | bk_valve | ...
    role = Column(String(50))

    # mqtt | modbus_tcp | modbus_rtu | http | gpio
    protocol = Column(String(20), default="mqtt")

    # Protocol-specific overrides (Modbus host/port/register, etc.)
    # MQTT devices need no extra config — topic is derived from device_key
    config = Column(JSON, default=dict)

    rig_id = Column(Integer, ForeignKey("rig_profiles.id"), nullable=True)

    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, nullable=True)
    current_value = Column(Float, nullable=True)
    current_unit = Column(String(10), nullable=True)

    rig = relationship("RigProfile", back_populates="devices")
    readings = relationship(
        "DeviceReading",
        back_populates="device",
        cascade="all, delete-orphan",
        order_by="DeviceReading.timestamp.desc()",
    )


class DeviceReading(Base):
    __tablename__ = "device_readings"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(10), default="C")
    timestamp = Column(DateTime, default=datetime.utcnow)

    device = relationship("Device", back_populates="readings")

    __table_args__ = (
        Index("ix_device_readings_device_ts", "device_id", "timestamp"),
    )
