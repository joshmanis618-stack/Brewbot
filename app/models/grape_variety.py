from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class GrapeVariety(Base):
    __tablename__ = "grape_varieties"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    color = Column(String(20))      # red, white, rosé
    origin = Column(String(100))
    notes = Column(Text)

    recipe_grapes = relationship("RecipeGrape", back_populates="grape")


class RecipeGrape(Base):
    __tablename__ = "recipe_grapes"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    grape_id = Column(Integer, ForeignKey("grape_varieties.id"), nullable=False)
    percentage = Column(Float)   # % of blend (optional)
    amount_kg = Column(Float)

    recipe = relationship("Recipe", back_populates="grapes")
    grape = relationship("GrapeVariety", back_populates="recipe_grapes", lazy="joined")
