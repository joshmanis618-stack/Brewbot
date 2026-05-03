from sqlalchemy import Column, Integer, String, Float, Text
from .base import Base


class Style(Base):
    __tablename__ = "styles"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    category = Column(String(100))
    style_guide = Column(String(50))          # e.g. "BJCP 2021"
    style_letter = Column(String(10))
    type = Column(String(20))                  # Ale, Lager, Mead, Cider, etc.

    og_min = Column(Float)
    og_max = Column(Float)
    fg_min = Column(Float)
    fg_max = Column(Float)
    ibu_min = Column(Float)
    ibu_max = Column(Float)
    color_min = Column(Float)                  # SRM
    color_max = Column(Float)
    abv_min = Column(Float)
    abv_max = Column(Float)
    carb_min = Column(Float)                   # volumes CO2
    carb_max = Column(Float)

    notes = Column(Text)
    profile = Column(Text)
    ingredients = Column(Text)
    examples = Column(Text)
