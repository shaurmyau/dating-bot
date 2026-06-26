from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, String
from sqlalchemy.sql import func
from .database import Base

class Like(Base):
    __tablename__ = 'likes'
    
    id = Column(Integer, primary_key=True)
    from_profile_id = Column(Integer, ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False)
    to_profile_id = Column(Integer, ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False)
    like_type = Column(String(16), nullable=False)  # 'like' или 'dislike'
    is_mutual = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())