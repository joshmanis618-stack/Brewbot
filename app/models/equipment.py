from sqlalchemy import Column, Integer, String, Float, Text, Boolean
from .base import Base


class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)

    batch_size_l = Column(Float, nullable=False)      # target post-boil volume
    boil_size_l = Column(Float, nullable=False)       # pre-boil volume
    boil_time_min = Column(Integer, default=60)

    efficiency = Column(Float, default=75.0)          # mash efficiency %
    hop_utilization = Column(Float, default=100.0)    # % adjustment for hop utilization

    trub_chiller_loss_l = Column(Float, default=1.0)
    lauter_deadspace_l = Column(Float, default=0.0)
    top_up_water_l = Column(Float, default=0.0)       # water added post-boil

    notes = Column(Text)
