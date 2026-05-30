# fishing_models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
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

class PlayerStats(Base):
    __tablename__ = "player_stats"
    id              = Column(Integer, primary_key=True)
    user_id         = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    total_distance_m = Column(Float, default=0.0)
    total_sessions  = Column(Integer, default=0)
    updated_at      = Column(DateTime, default=datetime.utcnow)

class AchievementUnlock(Base):
    __tablename__ = "achievement_unlocks"
    id             = Column(Integer, primary_key=True)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(String, nullable=False)
    unlocked_at    = Column(DateTime, default=datetime.utcnow)
