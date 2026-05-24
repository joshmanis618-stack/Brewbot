from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
import enum
from .base import Base


class RecipeType(str, enum.Enum):
    all_grain = "All Grain"
    extract = "Extract"
    partial_mash = "Partial Mash"


class HopUse(str, enum.Enum):
    boil = "Boil"
    dry_hop = "Dry Hop"
    first_wort = "First Wort"
    aroma = "Aroma"
    mash = "Mash"


class HopForm(str, enum.Enum):
    pellet = "Pellet"
    plug = "Plug"
    leaf = "Leaf"


class MiscUse(str, enum.Enum):
    boil = "Boil"
    mash = "Mash"
    primary = "Primary"
    secondary = "Secondary"
    bottling = "Bottling"


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), default=RecipeType.all_grain)
    style_id = Column(Integer, ForeignKey("styles.id"), nullable=True)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=True)

    batch_size_l = Column(Float, nullable=False)
    boil_size_l = Column(Float)
    boil_time_min = Column(Integer, default=60)
    efficiency = Column(Float, default=75.0)

    # Calculated targets
    og = Column(Float)
    fg = Column(Float)
    abv = Column(Float)
    ibu = Column(Float)
    color_srm = Column(Float)

    # Multi-craft
    craft = Column(String(20), default="beer")  # beer, wine, spirits

    # Wine-specific
    wine_style = Column(String(20))          # red, white, rosé, orange
    skin_contact_days = Column(Integer)      # days on skins (red / orange wines)
    target_ta = Column(Float)                # titratable acidity g/L
    target_ph = Column(Float)

    notes = Column(Text)
    brewer = Column(String(100))
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    style = relationship("Style", lazy="joined")
    equipment = relationship("Equipment", lazy="joined")
    fermentables = relationship("RecipeFermentable", back_populates="recipe", cascade="all, delete-orphan")
    hops = relationship("RecipeHop", back_populates="recipe", cascade="all, delete-orphan")
    yeasts = relationship("RecipeYeast", back_populates="recipe", cascade="all, delete-orphan")
    miscs = relationship("RecipeMisc", back_populates="recipe", cascade="all, delete-orphan")
    grapes = relationship("RecipeGrape", back_populates="recipe", cascade="all, delete-orphan")
    brew_sessions = relationship("BrewSession", back_populates="recipe", cascade="all, delete-orphan")
    brew_programs = relationship("BrewProgram", back_populates="recipe", cascade="all, delete-orphan")


class RecipeFermentable(Base):
    __tablename__ = "recipe_fermentables"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    fermentable_id = Column(Integer, ForeignKey("fermentables.id"), nullable=False)
    amount_kg = Column(Float, nullable=False)
    add_after_boil = Column(Boolean, default=False)

    recipe = relationship("Recipe", back_populates="fermentables")
    fermentable = relationship("Fermentable", lazy="joined")


class RecipeHop(Base):
    __tablename__ = "recipe_hops"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    hop_id = Column(Integer, ForeignKey("hops.id"), nullable=False)
    amount_g = Column(Float, nullable=False)
    time_min = Column(Integer, default=60)
    use = Column(String(20), default=HopUse.boil)
    form = Column(String(20), default=HopForm.pellet)

    recipe = relationship("Recipe", back_populates="hops")
    hop = relationship("Hop", lazy="joined")


class RecipeYeast(Base):
    __tablename__ = "recipe_yeasts"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    yeast_id = Column(Integer, ForeignKey("yeasts.id"), nullable=False)
    amount = Column(Float, default=1.0)   # packets / vials
    add_to_secondary = Column(Boolean, default=False)

    recipe = relationship("Recipe", back_populates="yeasts")
    yeast = relationship("Yeast", lazy="joined")


class RecipeMisc(Base):
    __tablename__ = "recipe_miscs"

    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    misc_id = Column(Integer, ForeignKey("miscs.id"), nullable=False)
    amount = Column(Float, nullable=False)
    amount_is_weight = Column(Boolean, default=True)   # True = grams, False = ml
    time_min = Column(Integer, default=0)
    use = Column(String(20), default=MiscUse.boil)

    recipe = relationship("Recipe", back_populates="miscs")
    misc = relationship("Misc", lazy="joined")
