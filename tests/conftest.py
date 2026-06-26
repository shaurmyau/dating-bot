import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date
import fakeredis
from bot.services.cache_service import CacheService

# Явно импортируем все модули моделей, чтобы они зарегистрировались в Base.metadata
import bot.models.user
import bot.models.profile
import bot.models.like
import bot.models.match
import bot.models.photo
import bot.models.views_history
import bot.models.chat
import bot.models.message

from bot.models.database import Base
from bot.models.user import User
from bot.models.profile import Profile

# Используем in-memory SQLite с включёнными внешними ключами
TEST_DATABASE_URL = "sqlite:///:memory:?foreign_keys=on"

@pytest.fixture(scope="function", autouse=True)
def db_session(monkeypatch):
    """Создаёт изолированную сессию и подменяет её во всех сервисах."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Подменяем глобальную сессию во всех модулях, где она используется
    monkeypatch.setattr('bot.models.database.db_session', session)
    monkeypatch.setattr('bot.services.user_service.db_session', session)
    monkeypatch.setattr('bot.services.matching_service.db_session', session)
    monkeypatch.setattr('bot.services.ranking_service.db_session', session)

    yield session

    session.rollback()
    session.close()
    Base.metadata.drop_all(engine)

@pytest.fixture
def sample_user(db_session):
    user = User(
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User"
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def sample_profile(db_session, sample_user):
    profile = Profile(
        user_id=sample_user.id,
        gender="male",
        birth_date=date(1995, 5, 15),
        city="Moscow",
        bio="Test bio",
        search_gender="female",
        search_age_min=20,
        search_age_max=30,
        search_distance_km=50,
        is_completed=True
    )
    db_session.add(profile)
    db_session.commit()
    return profile

@pytest.fixture
def fake_redis():
    redis_client = fakeredis.FakeRedis(decode_responses=True)
    original_init = CacheService.__init__
    CacheService.__init__ = lambda self: setattr(self, 'redis_client', redis_client)
    yield redis_client
    CacheService.__init__ = original_init