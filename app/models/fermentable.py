from sqlalchemy import Column, Integer, String, Float, Text, Boolean
from .base import Base


class Fermentable(Base):
    """Ingredient library entry for grains, extracts, sugars, and adjuncts."""
    __tablename__ = "fermentables"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)   # Grain, Sugar, Extract, Dry Extract, Adjunct
    origin = Column(String(100))
    supplier = Column(String(100))

    color_srm = Column(Float, nullable=False, default=0.0)
    potential = Column(Float, default=1.037)     # SG potential per pound per gallon
    yield_pct = Column(Float, default=75.0)      # coarse/fine extract %
    moisture_pct = Column(Float, default=4.0)
    diastatic_power = Column(Float, default=0.0) # Lintner
    protein_pct = Column(Float)
    max_in_batch_pct = Column(Float)

    add_after_boil = Column(Boolean, default=False)
    recommend_mash = Column(Boolean, default=True)

    notes = Column(Text)
