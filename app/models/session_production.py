from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, Date
from sqlalchemy.orm import relationship
from .base import Base


class SessionDryHop(Base):
    __tablename__ = "session_dry_hops"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("brew_sessions.id"), nullable=False)
    hop_id = Column(Integer, ForeignKey("hops.id"), nullable=True)
    variety = Column(String(100), nullable=True)
    addition_date = Column(Date, nullable=True)
    removal_date = Column(Date, nullable=True)
    rate_g_per_l = Column(Float, nullable=True)
    total_grams = Column(Float, nullable=True)
    temp_c = Column(Float, nullable=True)
    vessel = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)

    session = relationship("BrewSession", back_populates="dry_hops")
    hop = relationship("Hop", lazy="joined")


class PackagingEntry(Base):
    __tablename__ = "packaging_entries"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("brew_sessions.id"), nullable=False)
    package_date = Column(Date, nullable=True)
    method = Column(String(20), nullable=True)   # bottle/keg/can/cask
    vessel_count = Column(Integer, nullable=True)
    fill_volume_l = Column(Float, nullable=True)
    carbonation_vol = Column(Float, nullable=True)
    priming_sugar_type = Column(String(50), nullable=True)
    priming_sugar_g = Column(Float, nullable=True)
    co2_psi = Column(Float, nullable=True)
    final_gravity = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    session = relationship("BrewSession", back_populates="packaging_entries")
