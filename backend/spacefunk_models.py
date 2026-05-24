# spacefunk_models.py
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from database import Base
from datetime import datetime

# Max individual run rows kept per user. Oldest are pruned when exceeded.
SF_MAX_RUNS = 50


class SpaceFunkRun(Base):
    __tablename__ = "spacefunk_runs"
    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    score       = Column(Integer, default=0)
    distance_m  = Column(Float, default=0.0)
    played_at   = Column(DateTime, default=datetime.utcnow)


class SpaceFunkStats(Base):
    """One row per user — cumulative totals, updated on every run."""
    __tablename__ = "spacefunk_stats"
    user_id          = Column(Integer, ForeignKey("users.id"), primary_key=True)
    total_runs       = Column(Integer, default=0)
    total_distance_m = Column(Float,   default=0.0)
    best_score       = Column(Integer, default=0)
