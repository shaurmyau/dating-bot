import logging
from bot.models.database import db_session
from bot.models.like import Like
from bot.models.match import Match
from bot.services.user_service import UserService
from bot.services.cache_service import CacheService
from bot.models.profile import Profile
from bot.metrics import total_likes, total_matches

logger = logging.getLogger(__name__)
cache_service = CacheService()

class MatchingService:
    @staticmethod
    def add_like(from_profile_id: int, to_profile_id: int) -> bool:
        """Добавляет лайк, проверяет взаимность"""
        existing = db_session.query(Like).filter_by(
            from_profile_id=from_profile_id,
            to_profile_id=to_profile_id
        ).first()
        if existing:
            return False
        
        like = Like(from_profile_id=from_profile_id, to_profile_id=to_profile_id, like_type='like')
        db_session.add(like)
        
        # Проверка на взаимный лайк
        mutual = db_session.query(Like).filter_by(
            from_profile_id=to_profile_id,
            to_profile_id=from_profile_id,
            like_type='like'
        ).first()
        
        if mutual:
            like.is_mutual = True
            mutual.is_mutual = True
            # Создаём мэтч
            match = Match(profile1_id=from_profile_id, profile2_id=to_profile_id)
            db_session.add(match)
            total_matches.inc()
            logger.info(f"Match created between {from_profile_id} and {to_profile_id}")
        
        db_session.commit()
        
        # Сбросить кэш очереди для обоих пользователей
        from_profile_user = db_session.query(Profile).get(from_profile_id).user
        to_profile_user = db_session.query(Profile).get(to_profile_id).user
        cache_service.redis_client.delete(f"feed_queue:{from_profile_user.telegram_id}")
        cache_service.redis_client.delete(f"feed_queue:{to_profile_user.telegram_id}")
        return True

    @staticmethod
    def add_dislike(from_profile_id: int, to_profile_id: int) -> bool:
        existing = db_session.query(Like).filter_by(
            from_profile_id=from_profile_id,
            to_profile_id=to_profile_id
        ).first()
        if existing:
            return False
        dislike = Like(from_profile_id=from_profile_id, to_profile_id=to_profile_id, like_type='dislike')
        db_session.add(dislike)
        db_session.commit()
        return True