from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .base import Base


class BrewProgram(Base):
    __tablename__ = "brew_programs"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    steps = relationship(
        "BrewStep",
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="BrewStep.step_number",
    )
    recipe = relationship("Recipe", back_populates="brew_programs")


class BrewStep(Base):
    __tablename__ = "brew_steps"

    id = Column(Integer, primary_key=True)
    program_id = Column(Integer, ForeignKey("brew_programs.id", ondelete="CASCADE"), nullable=False)
    step_number = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)

    trigger_type = Column(String(20), default="manual")
    trigger_value = Column(Float, nullable=True)
    trigger_device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)

    program = relationship("BrewProgram", back_populates="steps")
    commands = relationship(
        "BrewStepCommand",
        back_populates="step",
        cascade="all, delete-orphan",
    )
    trigger_device = relationship("Device", foreign_keys=[trigger_device_id])


class BrewStepCommand(Base):
    __tablename__ = "brew_step_commands"

    id = Column(Integer, primary_key=True)
    step_id = Column(Integer, ForeignKey("brew_steps.id", ondelete="CASCADE"), nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    command = Column(String(50), nullable=False)

    step = relationship("BrewStep", back_populates="commands")
    device = relationship("Device", foreign_keys=[device_id])


class BrewSessionStep(Base):
    __tablename__ = "brew_session_steps"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("brew_sessions.id", ondelete="CASCADE"), nullable=False)
    step_id = Column(Integer, ForeignKey("brew_steps.id"), nullable=False)
    status = Column(String(20), default="pending")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    step = relationship("BrewStep")
    session = relationship("BrewSession", back_populates="brew_session_steps")
