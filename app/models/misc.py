from sqlalchemy import Column, Integer, String, Text
from .base import Base


class Misc(Base):
    """Ingredient library entry for miscellaneous additions (water agents, finings, spices, etc.)."""
    __tablename__ = "miscs"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(String(30))    # Spice, Fining, Water Agent, Herb, Flavor, Other
    use_for = Column(Text)
    notes = Column(Text)
