from sqlalchemy import Column, Integer, String, Float, Text
from .base import Base


class Yeast(Base):
    """Ingredient library entry for yeast strains."""
    __tablename__ = "yeasts"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    lab = Column(String(100))
    product_id = Column(String(50))
    type = Column(String(20))           # Ale, Lager, Wheat, Wine, Champagne
    form = Column(String(20))           # Liquid, Dry

    min_temp_c = Column(Float)
    max_temp_c = Column(Float)
    attenuation_pct = Column(Float, default=75.0)
    flocculation = Column(String(20))   # Low, Medium, High, Very High
    best_for = Column(Text)

    notes = Column(Text)
