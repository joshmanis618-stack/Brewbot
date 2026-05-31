from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .base import Base


class BrewSession(Base):
    __tablename__ = "brew_sessions"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=True)
    craft = Column(String(20), default="beer")  # beer, wine, spirits

    status = Column(String(20), default="planned")   # planned, brewing, fermenting, conditioning, complete
    brew_date = Column(DateTime, nullable=True)
    package_date = Column(DateTime, nullable=True)

    # Actual measurements
    actual_og = Column(Float)
    actual_fg = Column(Float)
    actual_abv = Column(Float)
    actual_batch_size_l = Column(Float)
    actual_efficiency = Column(Float)

    # Fermentation tracking
    ferment_temp_c = Column(Float)

    # Wine harvest intake (populated once at crush/intake)
    brix_intake = Column(Float)             # Brix at crush
    ph_intake = Column(Float)               # pH at intake
    ta_intake_g_l = Column(Float)           # titratable acidity g/L
    fruit_weight_kg = Column(Float)         # total fruit/must weight
    crush_date = Column(DateTime)           # date of crush/pressing
    fruit_source = Column(String(300))      # vineyard, supplier, variety

    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    recipe = relationship("Recipe", back_populates="brew_sessions")
    equipment = relationship("Equipment")
    barrel_aging_records = relationship(
        "BarrelAgingRecord",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    brew_session_steps = relationship(
        "BrewSessionStep",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    fermentation_readings = relationship(
        "FermentationReading",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="FermentationReading.recorded_at",
    )
    mlf_entries = relationship(
        "WineMLFEntry",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="WineMLFEntry.recorded_at",
    )
    fining_entries = relationship(
        "WineFiningEntry",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="WineFiningEntry.date",
    )
    still_runs = relationship(
        "StillRun",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="StillRun.run_number",
    )
