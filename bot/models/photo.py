from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from .database import Base
from bot.models.database import db_session

class Photo(Base):
    __tablename__ = 'photos'
    
    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False)
    s3_key = Column(String(512), nullable=False)
    order_index = Column(Integer, default=0)
    is_main = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
    @property
    def photo_count(self):
        return db_session.query(Photo).filter_by(profile_id=self.id).count()