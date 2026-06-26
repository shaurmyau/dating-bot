import logging
from sqlalchemy.exc import IntegrityError
from bot.models.database import db_session
from bot.models.user import User
from bot.models.profile import Profile
from sqlalchemy.sql import func
from bot.services.cache_service import CacheService as cache_service
from bot.models.profile import Profile
from sqlalchemy import not_

logger = logging.getLogger(__name__)

class UserService:
    """Сервис для работы с пользователями"""
    
    @staticmethod
    def get_or_create_user(telegram_id: int, username: str = None, 
                           first_name: str = None, last_name: str = None) -> User:
        """
        Получить или создать пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            username: Username пользователя
            first_name: Имя пользователя
            last_name: Фамилия пользователя
            
        Returns:
            User: Объект пользователя
        """
        try:
            user = db_session.query(User).filter_by(telegram_id=telegram_id).first()
            
            if user:
                # Обновляем данные если изменились
                updated = False
                if username and user.username != username:
                    user.username = username
                    updated = True
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                    updated = True
                if last_name and user.last_name != last_name:
                    user.last_name = last_name
                    updated = True
                
                if updated:
                    db_session.commit()
                    logger.info(f"Updated user {telegram_id}")
            else:
                # Создаем нового пользователя
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                db_session.add(user)
                db_session.commit()
                logger.info(f"Created new user {telegram_id}")
            
            return user
            
        except IntegrityError as e:
            db_session.rollback()
            logger.error(f"Error creating user {telegram_id}: {e}")
            raise
        except Exception as e:
            db_session.rollback()
            logger.error(f"Unexpected error in get_or_create_user: {e}")
            raise
    
    @staticmethod
    def get_user_by_telegram_id(telegram_id: int) -> User:
        """Получить пользователя по Telegram ID"""
        return db_session.query(User).filter_by(telegram_id=telegram_id).first()
    
    @staticmethod
    def get_user_profile(user_id: int) -> Profile:
        """Получить профиль пользователя"""
        return db_session.query(Profile).filter_by(user_id=user_id).first()
    
    @staticmethod
    def is_user_registered(telegram_id: int) -> bool:
        """
        Проверить, зарегистрирован ли пользователь (имеет ли заполненную анкету)
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            bool: True если пользователь зарегистрирован, False в противном случае
        """
        user = UserService.get_user_by_telegram_id(telegram_id)
        if not user:
            return False
        
        profile = UserService.get_user_profile(user.id)
        return profile is not None and profile.is_completed
    
    @staticmethod
    def update_user_activity(telegram_id: int):
        """Обновить время последней активности пользователя"""
        user = UserService.get_user_by_telegram_id(telegram_id)
        if user:
            user.updated_at = func.now()
            db_session.commit()
            
            
    @staticmethod
    def delete_user_account(telegram_id: int) -> bool:
        """
        Полное удаление аккаунта пользователя и всех связанных данных
        """
        import traceback
        try:
            logger.info(f"Starting deletion for user {telegram_id}")
            
            # Находим пользователя
            user = db_session.query(User).filter_by(telegram_id=telegram_id).first()
            
            if not user:
                logger.warning(f"User {telegram_id} not found for deletion")
                return False
            
            logger.info(f"Found user: id={user.id}, telegram_id={user.telegram_id}")
            
            # Находим профиль пользователя
            profile = db_session.query(Profile).filter_by(user_id=user.id).first()
            
            if profile:
                logger.info(f"Found profile: id={profile.id}, user_id={profile.user_id}")
                # Удаляем профиль
                db_session.delete(profile)
                logger.info(f"Profile {profile.id} marked for deletion")
            else:
                logger.info(f"No profile found for user {telegram_id}")
            
            # Удаляем пользователя
            db_session.delete(user)
            logger.info(f"User {user.id} marked for deletion")
            
            # Коммитим изменения
            db_session.commit()
            logger.info(f"User account {telegram_id} deleted successfully")
            return True
            
        except Exception as e:
            db_session.rollback()
            logger.error(f"Error deleting user account {telegram_id}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
        
    @staticmethod
    def update_profile(telegram_id: int, **kwargs) -> bool:
        user = UserService.get_user_by_telegram_id(telegram_id)
        if not user:
            return False
        profile = db_session.query(Profile).filter_by(user_id=user.id).first()
        if not profile:
            return False
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        db_session.commit()
        # сбросить кэш
        from bot.services.cache_service import CacheService
        cache = CacheService()
        cache.delete_cached_profile(profile.id)
        return True

    @staticmethod
    def get_profile_for_ranking(viewer_telegram_id: int, limit: int = 50) -> list[int]:
        """
        Возвращает список profile_id, отсортированных по combined_rank (от высшего к низшему).
        viewer_telegram_id – Telegram ID пользователя, который смотрит анкеты.
        limit – максимальное количество возвращаемых анкет.
        """
        from bot.models.views_history import ViewsHistory
        from bot.services.ranking_service import RankingService

        # 1. Найти текущего пользователя и его профиль
        viewer_user = UserService.get_user_by_telegram_id(viewer_telegram_id)
        if not viewer_user:
            return []
        viewer_profile = UserService.get_user_profile(viewer_user.id)
        if not viewer_profile or not viewer_profile.is_completed:
            return []

        # 2. Загрузить все активные профили, кроме своего и исключая просмотренные
        viewed_ids = db_session.query(ViewsHistory.viewed_profile_id).filter(
            ViewsHistory.viewer_profile_id == viewer_profile.id
        ).subquery()

        other_profiles = db_session.query(Profile).join(Profile.user).filter(
            Profile.is_completed == True,
            User.is_active == True,
            User.telegram_id != viewer_telegram_id,
            Profile.id.notin_(viewed_ids)   # исключаем просмотренные
        ).all()

        # 3. Вычислить рейтинг для каждого профиля
        ranked = []
        for profile in other_profiles:
            rank = RankingService.combined_rank(profile, viewer_profile, profile.id)
            ranked.append((profile.id, rank))

        # 4. Сортировка по убыванию рейтинга
        ranked.sort(key=lambda x: x[1], reverse=True)

        # 5. Вернуть только ID профилей (ограничиваем количество)
        return [profile_id for profile_id, _ in ranked[:limit]]
    
    @staticmethod
    def update_profile(telegram_id: int, **kwargs) -> bool:
        """
        Обновляет поля анкеты пользователя.
        Допустимые ключи: gender, birth_date, city, bio, search_gender,
        search_age_min, search_age_max, search_distance_km
        """
        from bot.models.profile import Profile
        user = UserService.get_user_by_telegram_id(telegram_id)
        if not user:
            return False
        profile = db_session.query(Profile).filter_by(user_id=user.id).first()
        if not profile:
            return False
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        profile.updated_at = func.now()
        db_session.commit()
        # Сброс кэша
        from bot.services.cache_service import CacheService
        cache = CacheService()
        cache.delete_cached_profile(profile.id)
        return True