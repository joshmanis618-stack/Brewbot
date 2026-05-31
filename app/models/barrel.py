from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, ForeignKey, DateTime, Date
from sqlalchemy.orm import relationship
from .base import Base

# 53-gallon barrel reference: ~75 cm²/L at 15°C cellar temperature.
# Geometric scaling for traditional barrels: SA:V = K / V^(1/3) where K is
# calibrated so that V=200L gives 75 cm²/L → K = 75 * 200^(1/3) ≈ 438.6
_SAV_K = 75.0 * (200.0 ** (1.0 / 3.0))
_REF_SAV = 75.0   # cm²/L — 53-gallon benchmark
_REF_TEMP = 15.0  # °C — cellar reference temperature


class Barrel(Base):
    __tablename__ = "barrels"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    barrel_style = Column(String(20), default='traditional')  # 'traditional' | 'bad_motivator'
    size_l = Column(Float, nullable=False)
    wood_type = Column(String(50))
    char_level = Column(String(50))
    previous_contents = Column(String(100))
    age_months = Column(Integer)
    wood_contact_area_cm2 = Column(Float, nullable=True)  # Bad Motivator: explicit wood surface
    storage_temp_c = Column(Float, nullable=True)         # average storage temp for rate calc
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    aging_records = relationship("BarrelAgingRecord", back_populates="barrel")

    @property
    def effective_sav(self):
        """Wood-contact surface area to volume ratio in cm²/L."""
        if not self.size_l:
            return None
        if self.barrel_style == 'bad_motivator':
            if self.wood_contact_area_cm2:
                return round(self.wood_contact_area_cm2 / self.size_l, 1)
            return None
        return round(_SAV_K / (self.size_l ** (1.0 / 3.0)), 1)

    @property
    def aging_multiplier(self):
        """Total aging rate vs. 53-gal barrel at 15°C cellar (SA:V × temperature factors)."""
        sav = self.effective_sav
        if sav is None:
            return None
        temp = self.storage_temp_c if self.storage_temp_c is not None else _REF_TEMP
        sa_factor = sav / _REF_SAV
        temp_factor = 2.0 ** ((temp - _REF_TEMP) / 10.0)
        return round(sa_factor * temp_factor, 2)

    @property
    def target_wood_area_cm2(self):
        """Wood contact area needed to match 53-gal SA:V for this vessel volume."""
        if not self.size_l:
            return None
        return round(_REF_SAV * self.size_l)


class BarrelAgingRecord(Base):
    __tablename__ = "barrel_aging_records"

    id = Column(Integer, primary_key=True)
    barrel_id = Column(Integer, ForeignKey("barrels.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("brew_sessions.id"), nullable=False)
    start_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    target_days = Column(Integer, nullable=True)
    target_55gal_months = Column(Float, nullable=True)  # planned equivalent 55-gal aging depth
    notes = Column(Text)

    fill_proof = Column(Float, nullable=True)         # proof at fill (ABV × 2, US standard)
    disposition = Column(String(30), default='aging')  # aging, dumped, bottled, re-casked, blended

    barrel = relationship("Barrel", back_populates="aging_records")
    session = relationship("BrewSession", back_populates="barrel_aging_records")
    entries = relationship(
        "BarrelAgingEntry",
        back_populates="record",
        cascade="all, delete-orphan",
        order_by="BarrelAgingEntry.recorded_at",
    )
    disposition_entries = relationship(
        "BarrelDispositionEntry",
        back_populates="record",
        cascade="all, delete-orphan",
        order_by="BarrelDispositionEntry.event_date",
    )


class BarrelAgingEntry(Base):
    __tablename__ = "barrel_aging_entries"

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey("barrel_aging_records.id"), nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    gravity = Column(Float)
    abv = Column(Float)
    color_srm = Column(Float, nullable=True)  # color in SRM (1=pale straw → 40+=black)
    flavor_notes = Column(Text)
    notes = Column(Text)

    record = relationship("BarrelAgingRecord", back_populates="entries")


class BarrelDispositionEntry(Base):
    __tablename__ = "barrel_disposition_entries"

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey("barrel_aging_records.id"), nullable=False)
    event_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    action = Column(String(50), nullable=False)  # dumped, bottled, re-casked, blended, sampled, proof check
    proof_at_action = Column(Float, nullable=True)
    volume_l = Column(Float, nullable=True)
    destination = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)

    record = relationship("BarrelAgingRecord", back_populates="disposition_entries")
