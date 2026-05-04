from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from .base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(200), unique=True, nullable=True)
    password_hash = Column(String(200), nullable=False)
    totp_secret = Column(String(64), nullable=True)
    totp_enabled = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
