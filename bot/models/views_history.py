from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from .database import Base

class ViewsHistory(Base):
    __tablename__ = 'views_history'

    id = Column(Integer, primary_key=True)
    viewer_profile_id = Column(Integer, ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False)
    viewed_profile_id = Column(Integer, ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False)
    viewed_at = Column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint('viewer_profile_id', 'viewed_profile_id', name='unique_view'),)