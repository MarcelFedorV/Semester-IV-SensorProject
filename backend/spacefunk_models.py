# spacefunk_models.py
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from database import Base
from datetime import datetime


class SpaceFunkRun(Base):
    __tablename__ = "spacefunk_runs"
    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    score       = Column(Integer, default=0)
    distance_m  = Column(Float, default=0.0)
    played_at   = Column(DateTime, default=datetime.utcnow)
