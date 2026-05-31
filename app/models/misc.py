from sqlalchemy import Column, Integer, String, Float, Text
from .base import Base


class Misc(Base):
    """Ingredient library entry for miscellaneous additions (water agents, finings, spices, etc.)."""
    __tablename__ = "miscs"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(String(30))    # Spice, Fining, Water Agent, Herb, Flavor, Other
    use_for = Column(Text)
    notes = Column(Text)

    stock_qty = Column(Float, nullable=True, default=0.0)
    stock_unit = Column(String(10), nullable=True, default="g")
    cost_per_unit = Column(Float, nullable=True)
