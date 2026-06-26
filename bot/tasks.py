from celery import shared_task
from bot.services.matching_service import MatchingService
from bot.metrics import active_users
from bot.models.database import db_session
from bot.models.profile import Profile

@shared_task
def process_like_async(from_profile_id, to_profile_id):
    MatchingService.add_like(from_profile_id, to_profile_id)

@shared_task
def update_active_users_metric():
    """Обновление количества активных пользователей (с заполненной анкетой)"""
    count = db_session.query(Profile).filter_by(is_completed=True).count()
    active_users.set(count)
    return count