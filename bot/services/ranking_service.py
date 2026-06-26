import logging
from datetime import datetime, time
from sqlalchemy import func, and_
from bot.models.database import db_session
from bot.models.like import Like
from bot.models.match import Match
from bot.models.message import Message
from bot.models.profile import Profile
from bot.models.user import User

logger = logging.getLogger(__name__)

class RankingService:
    @staticmethod
    def primary_rank(profile: Profile, viewer_profile: Profile) -> float:
        """Первичный рейтинг на основе анкеты и предпочтений зрителя"""
        score = 0.0
        # Возраст
        age = profile.age
        if viewer_profile.search_age_min <= age <= viewer_profile.search_age_max:
            score += 0.3
        # Пол
        if profile.gender == viewer_profile.search_gender or viewer_profile.search_gender == 'any':
            score += 0.2
        # Город
        if profile.city == viewer_profile.city:
            score += 0.2
        # Полнота анкеты + фото
        photo_count = db_session.query(Like).filter_by(to_profile_id=profile.id, like_type='like').count()  # placeholder
        # Лучше получать через relationship, но для простоты:
        from bot.models.photo import Photo
        photo_count = db_session.query(Photo).filter_by(profile_id=profile.id).count()
        photo_score = min(photo_count / 5, 1.0) * 0.2
        bio_score = (len(profile.bio or '') / 500) * 0.1
        score += photo_score + bio_score
        return min(score, 1.0)

    @staticmethod
    def behavioral_rank(profile_id: int) -> float:
        """
        Поведенческий рейтинг на основе реальных взаимодействий:
        - количество лайков
        - соотношение лайков / (лайки + пропуски)
        - частота мэтчей (matches / лайки)
        - частота инициирования диалогов (первое сообщение после мэтча)
        """
        # 1. Лайки и пропуски
        likes = db_session.query(Like).filter_by(to_profile_id=profile_id, like_type='like').count()
        dislikes = db_session.query(Like).filter_by(to_profile_id=profile_id, like_type='dislike').count()
        total_views = likes + dislikes
        like_ratio = likes / total_views if total_views > 0 else 0

        # 2. Мэтчи (взаимные лайки)
        matches = db_session.query(Match).filter(
            (Match.profile1_id == profile_id) | (Match.profile2_id == profile_id)
        ).count()
        match_ratio = matches / (likes + 1)

        # 3. Инициированные диалоги после мэтча
        # Считаем количество чатов (сообщений), где пользователь отправил первое сообщение
        # Получаем самый ранний message в каждом чате, сравниваем sender_profile_id
        # Подзапрос: минимальная дата сообщения в чате
        first_messages = db_session.query(
            Message.chat_id,
            func.min(Message.created_at).label('first_msg_time')
        ).group_by(Message.chat_id).subquery()

        initiated = db_session.query(Message).join(
            first_messages,
            and_(Message.chat_id == first_messages.c.chat_id,
                 Message.created_at == first_messages.c.first_msg_time)
        ).filter(Message.sender_profile_id == profile_id).count()

        chat_ratio = initiated / (matches + 1)

        # Итоговый рейтинг
        score = (like_ratio * 0.5) + (match_ratio * 0.3) + (chat_ratio * 0.2)

        return min(score, 1.0)

    @staticmethod
    def combined_rank(profile: Profile, viewer_profile: Profile, profile_id: int) -> float:
        """Комбинированный рейтинг с весами 0.4 первичный, 0.6 поведенческий"""
        primary = RankingService.primary_rank(profile, viewer_profile)
        behavioral = RankingService.behavioral_rank(profile_id)
        return 0.4 * primary + 0.6 * behavioral