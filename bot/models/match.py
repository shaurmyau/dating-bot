from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from .database import Base

class Match(Base):
    __tablename__ = 'matches'
    
    id = Column(Integer, primary_key=True)
    profile1_id = Column(Integer, ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False)
    profile2_id = Column(Integer, ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, server_default=func.now())