from database import Base
from sqlalchemy import Column, Integer, String

class User(Base):
    __tablename__ = "users"
    id       = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    email    = Column(String, nullable=True)
    bio      = Column(String, nullable=True)
    age      = Column(Integer, nullable=True)
    favorite_game = Column(String, nullable=True)
    role     = Column(String, default="user", nullable=False)  # "admin" or "user"
    language = Column(String, default="en", nullable=False)  # "en" or "dk"