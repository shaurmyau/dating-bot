import pytest
from datetime import date
from bot.services.matching_service import MatchingService
from bot.models.like import Like
from bot.models.match import Match
from bot.models.profile import Profile
from bot.models.user import User  # добавить импорт

def test_add_like_no_mutual(db_session, sample_profile):
    # Создаём пользователя для profile2
    user2 = User(
        telegram_id=888,
        username="user2",
        first_name="User2"
    )
    db_session.add(user2)
    db_session.commit()

    # Создаём второй профиль, связанный с этим пользователем
    profile2 = Profile(
        user_id=user2.id,  # используем ID созданного пользователя
        gender="female",
        birth_date=date(1995, 1, 1),
        city="SPb",
        search_gender="male",
        search_age_min=18,
        search_age_max=40,
        is_completed=True
    )
    db_session.add(profile2)
    db_session.commit()

    result = MatchingService.add_like(sample_profile.id, profile2.id)
    assert result is True
    like = db_session.query(Like).filter_by(
        from_profile_id=sample_profile.id,
        to_profile_id=profile2.id
    ).first()
    assert like is not None
    assert like.is_mutual is False
    match = db_session.query(Match).filter(
        (Match.profile1_id == sample_profile.id) | (Match.profile2_id == sample_profile.id)
    ).first()
    assert match is None

def test_add_like_mutual(db_session, sample_profile):
    # Создаём пользователя для profile2
    user2 = User(
        telegram_id=888,
        username="user2",
        first_name="User2"
    )
    db_session.add(user2)
    db_session.commit()

    # Создаём второй профиль
    profile2 = Profile(
        user_id=user2.id,
        gender="female",
        birth_date=date(1995, 1, 1),
        city="SPb",
        search_gender="male",
        search_age_min=18,
        search_age_max=40,
        is_completed=True
    )
    db_session.add(profile2)
    db_session.commit()

    # Сначала лайк от profile2 к sample_profile
    like_existing = Like(
        from_profile_id=profile2.id,
        to_profile_id=sample_profile.id,
        like_type='like'
    )
    db_session.add(like_existing)
    db_session.commit()

    result = MatchingService.add_like(sample_profile.id, profile2.id)
    assert result is True

    match = db_session.query(Match).filter(
        (Match.profile1_id == sample_profile.id) & (Match.profile2_id == profile2.id)
    ).first()
    assert match is not None

    like1 = db_session.query(Like).filter_by(
        from_profile_id=sample_profile.id,
        to_profile_id=profile2.id
    ).first()
    like2 = db_session.query(Like).filter_by(
        from_profile_id=profile2.id,
        to_profile_id=sample_profile.id
    ).first()
    assert like1.is_mutual is True
    assert like2.is_mutual is True