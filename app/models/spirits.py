from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .base import Base


class StillRun(Base):
    __tablename__ = "still_runs"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("brew_sessions.id"), nullable=False)
    run_number = Column(Integer, default=1)
    run_date = Column(DateTime, default=datetime.utcnow)
    charge_volume_l = Column(Float)
    charge_abv = Column(Float)
    still_type = Column(String(20), default="pot")  # pot, column, reflux
    notes = Column(Text)

    session = relationship("BrewSession", back_populates="still_runs")
    cuts = relationship(
        "StillCut",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="StillCut.id",
    )


class StillCut(Base):
    __tablename__ = "still_cuts"

    id = Column(Integer, primary_key=True)
    still_run_id = Column(Integer, ForeignKey("still_runs.id"), nullable=False)
    cut_type = Column(String(20), nullable=False)  # foreshots, heads, hearts, tails
    volume_l = Column(Float)
    start_abv = Column(Float)
    end_abv = Column(Float)

    # Sensory evaluation
    appearance = Column(String(200))
    aroma = Column(Text)
    flavor = Column(Text)
    finish = Column(Text)
    overall_notes = Column(Text)

    run = relationship("StillRun", back_populates="cuts")
