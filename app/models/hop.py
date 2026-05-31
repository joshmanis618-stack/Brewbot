from sqlalchemy import Column, Integer, String, Float, Text
from .base import Base


class Hop(Base):
    """Ingredient library entry for hops."""
    __tablename__ = "hops"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    origin = Column(String(100))
    type = Column(String(20))          # Bittering, Aroma, Both

    alpha_pct = Column(Float, nullable=False)
    beta_pct = Column(Float)
    hsi = Column(Float)                # Hop Storage Index
    caryophyllene_pct = Column(Float)
    cohumulone_pct = Column(Float)
    myrcene_pct = Column(Float)
    humulene_pct = Column(Float)

    notes = Column(Text)
    substitutes = Column(Text)

    stock_qty = Column(Float, nullable=True, default=0.0)
    cost_per_kg = Column(Float, nullable=True)
