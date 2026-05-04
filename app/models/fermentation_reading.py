from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from .base import Base


class FermentationReading(Base):
    __tablename__ = "fermentation_readings"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("brew_sessions.id"), nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    gravity = Column(Float, nullable=True)          # SG e.g. 1.020
    temperature_c = Column(Float, nullable=True)    # Celsius
    notes = Column(String(200), nullable=True)

    session = relationship("BrewSession", back_populates="fermentation_readings")
