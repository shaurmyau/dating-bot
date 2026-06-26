import pytest
from datetime import date
from bot.services.ranking_service import RankingService
from bot.models.profile import Profile
from bot.models.like import Like
from bot.models.match import Match
from bot.models.message import Message
from bot.models.photo import Photo
from bot.models.user import User

def test_primary_rank(db_session, sample_profile):
    # Создаём пользователя для viewer_profile
    viewer_user = User(
        telegram_id=999,
        username="viewer",
        first_name="Viewer"
    )
    db_session.add(viewer_user)
    db_session.commit()

    # Создаём второго пользователя (зрителя)
    viewer_profile = Profile(
        user_id=viewer_user.id,
        gender="female",
        birth_date=date(1990, 1, 1),
        city="Moscow",
        search_gender="male",
        search_age_min=18,
        search_age_max=35,
        bio="",
        search_distance_km=100,
        is_completed=True
    )
    db_session.add(viewer_profile)
    db_session.commit()
    # Добавляем фото
    photo = Photo(profile_id=sample_profile.id, s3_key="key", is_main=True)
    db_session.add(photo)
    db_session.commit()

    rank = RankingService.primary_rank(sample_profile, viewer_profile)
    # Ожидаемый ранг: возраст (0.3) + пол (0.2) + город (0.2) + фото (0.2 * 1/5 = 0.04) + био (8/500*0.1=0.0016) = 0.7416
    assert 0.7 <= rank <= 1.0

def test_behavioral_rank(db_session, sample_profile):
    # Создаём пользователей для лайков
    profiles = []
    for i in range(997, 1000):
        user = User(telegram_id=i, username=f"user{i}")
        db_session.add(user)
        db_session.commit()
        p = Profile(
            user_id=user.id,
            gender="female",
            birth_date=date(1990,1,1),
            city="Moscow",
            search_gender="male",
            search_age_min=18,
            search_age_max=40,
            is_completed=True
        )
        db_session.add(p)
        profiles.append(p)
    db_session.commit()

    # Добавляем лайки (profile_id 999 и 998 лайкают sample_profile, 997 – дизлайк)
    like1 = Like(from_profile_id=profiles[2].id, to_profile_id=sample_profile.id, like_type='like')  # 999
    like2 = Like(from_profile_id=profiles[1].id, to_profile_id=sample_profile.id, like_type='like')  # 998
    dislike = Like(from_profile_id=profiles[0].id, to_profile_id=sample_profile.id, like_type='dislike')  # 997
    db_session.add_all([like1, like2, dislike])
    db_session.commit()

    # Создаём мэтч с одним из профилей
    match = Match(profile1_id=sample_profile.id, profile2_id=profiles[2].id)
    db_session.add(match)
    db_session.commit()

    # Создаём сообщение (инициация диалога) – отправляет sample_profile
    msg = Message(chat_id=1, sender_profile_id=sample_profile.id, message_text="Hello")
    db_session.add(msg)
    db_session.commit()

    rank = RankingService.behavioral_rank(sample_profile.id)
    # like_ratio = 2/3 ≈0.667, match_ratio = 1/(2+1)=0.333, chat_ratio = 1/(1+1)=0.5
    # score = 0.667*0.5 + 0.333*0.3 + 0.5*0.2 ≈0.333+0.1+0.1=0.533
    assert 0.5 <= rank <= 0.6