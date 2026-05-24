from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class WineMLFEntry(Base):
    __tablename__ = "wine_mlf_entries"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("brew_sessions.id"), nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    event_type = Column(String(30), nullable=False)   # inoculation | test | complete
    strain = Column(String(100))                       # MLB strain (inoculation only)
    temperature_c = Column(Float)
    result = Column(String(20))                        # positive | negative | complete
    notes = Column(String(300))

    session = relationship("BrewSession", back_populates="mlf_entries")


class WineFiningEntry(Base):
    __tablename__ = "wine_fining_entries"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("brew_sessions.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow, nullable=False)
    agent = Column(String(100), nullable=False)        # Bentonite, Gelatin, Egg White…
    rate_g_per_hl = Column(Float)                      # dosage rate g/hL
    volume_l = Column(Float)                           # volume treated (L)
    purpose = Column(String(200))                      # protein stability, clarity…
    notes = Column(String(300))

    session = relationship("BrewSession", back_populates="fining_entries")
