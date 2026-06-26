import pytest
from bot.services.user_service import UserService
from bot.models.user import User

def test_get_or_create_user_new(db_session):
    user = UserService.get_or_create_user(
        telegram_id=111,
        username="new",
        first_name="New",
        last_name="User"
    )
    assert user.id is not None
    assert user.telegram_id == 111
    assert db_session.query(User).count() == 1

def test_get_or_create_user_existing(db_session, sample_user):
    user = UserService.get_or_create_user(
        telegram_id=sample_user.telegram_id,
        username="updated",
        first_name="Updated"
    )
    assert user.id == sample_user.id
    assert user.username == "updated"

def test_is_user_registered(db_session, sample_user, sample_profile):
    assert UserService.is_user_registered(sample_user.telegram_id) is True
    # Проверка для незарегистрированного
    assert UserService.is_user_registered(999) is False

def test_delete_user_account(db_session, sample_user, sample_profile):
    assert UserService.delete_user_account(sample_user.telegram_id) is True
    assert db_session.query(User).filter_by(telegram_id=sample_user.telegram_id).first() is None

def test_update_profile(db_session, sample_user, sample_profile):
    success = UserService.update_profile(sample_user.telegram_id, city="SPb", bio="new bio")
    assert success is True
    db_session.refresh(sample_profile)
    assert sample_profile.city == "SPb"
    assert sample_profile.bio == "new bio"