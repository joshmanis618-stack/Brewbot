from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .base import Base


class BrewSession(Base):
    __tablename__ = "brew_sessions"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=True)  # override

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

    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    recipe = relationship("Recipe", back_populates="brew_sessions")
    equipment = relationship("Equipment")
