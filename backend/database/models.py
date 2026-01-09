# backend/models.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    current_role = Column(String, default="Data Scientist")
    
    resume_text = Column(Text, nullable=True) 
    
    interviews = relationship("Interview", back_populates="owner")

class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    job_role = Column(String)
    resume_text = Column(Text)
    feedback_summary = Column(Text, nullable=True)
    score = Column(Integer, nullable=True)
    verdict = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="interviews")