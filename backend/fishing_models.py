# fishing_models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class FishCatch(Base):
    __tablename__ = "fish_catches"
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    fish_id    = Column(Integer, nullable=False)
    location_id = Column(Integer, nullable=False)
    depth      = Column(Float, nullable=False)
    caught_at  = Column(DateTime, default=datetime.utcnow)

class FishCollection(Base):
    __tablename__ = "fish_collection"
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    fish_id    = Column(Integer, nullable=False)
    first_caught_at = Column(DateTime, default=datetime.utcnow)

class Achievement(Base):
    __tablename__ = "achievements"
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(String, nullable=False)
    unlocked_at = Column(DateTime, default=datetime.utcnow)