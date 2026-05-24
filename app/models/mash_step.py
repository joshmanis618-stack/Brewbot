from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base


class MashStep(Base):
    __tablename__ = "mash_steps"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    name = Column(String(100))          # e.g. "Cereal Cook", "Saccharification", "Mash Out"
    temp_c = Column(Float, nullable=False)
    time_min = Column(Integer, nullable=False)
    additions = Column(Text)            # enzyme/grain additions at this step
    notes = Column(Text)

    recipe = relationship("Recipe", back_populates="mash_steps")
