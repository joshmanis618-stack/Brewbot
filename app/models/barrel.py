from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .base import Base


class Barrel(Base):
    __tablename__ = "barrels"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    size_l = Column(Float, nullable=False)
    wood_type = Column(String(50))       # American Oak, French Oak, Hungarian Oak, Cherry, Acacia
    char_level = Column(String(50))      # #1 Light, #2 Medium, #3 Heavy, #4 Extra Heavy; or Light/Medium/Heavy Toast
    previous_contents = Column(String(100))  # Bourbon, Red Wine, White Wine, Rum, Sherry, Port, New/Virgin
    age_months = Column(Integer)
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    aging_records = relationship("BarrelAgingRecord", back_populates="barrel")


class BarrelAgingRecord(Base):
    __tablename__ = "barrel_aging_records"

    id = Column(Integer, primary_key=True)
    barrel_id = Column(Integer, ForeignKey("barrels.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("brew_sessions.id"), nullable=False)
    start_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    target_days = Column(Integer, nullable=True)
    notes = Column(Text)

    barrel = relationship("Barrel", back_populates="aging_records")
    session = relationship("BrewSession", back_populates="barrel_aging_records")
    entries = relationship(
        "BarrelAgingEntry",
        back_populates="record",
        cascade="all, delete-orphan",
        order_by="BarrelAgingEntry.recorded_at",
    )


class BarrelAgingEntry(Base):
    __tablename__ = "barrel_aging_entries"

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey("barrel_aging_records.id"), nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    gravity = Column(Float)
    abv = Column(Float)
    flavor_notes = Column(Text)
    notes = Column(Text)

    record = relationship("BarrelAgingRecord", back_populates="entries")
