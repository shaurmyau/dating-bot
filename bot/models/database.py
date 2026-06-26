from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from config import config

# engine = create_engine(
#     config.DATABASE_URL,
#     echo=config.DEBUG,
#     pool_pre_ping=True
# )

engine = create_engine(
    config.DATABASE_URL, 
    pool_size=10, 
    max_overflow=20)

db_session = scoped_session(sessionmaker(bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    from . import user, profile, like, photo, match, views_history, chat, message
    Base.metadata.create_all(bind=engine)