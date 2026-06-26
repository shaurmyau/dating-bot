import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.services.cache_service import CacheService
from bot.services.user_service import UserService
from bot.models.database import db_session
from bot.models.profile import Profile
from bot.services.matching_service import MatchingService
from bot.models.views_history import ViewsHistory
from bot.tasks import process_like_async
from bot.metrics import total_likes, total_matches
from bot.metrics import measure_duration

logger = logging.getLogger(__name__)
cache_service = CacheService()

@measure_duration('feed_show')
async def show_next_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    viewer_user = UserService.get_user_by_telegram_id(user_id)
    viewer_profile = UserService.get_user_profile(viewer_user.id)
    queue_key = f"feed_queue:{user_id}"
    
    # Получаем очередь из Redis
    cached = cache_service.redis_client.get(queue_key)
    if cached:
        profile_ids = json.loads(cached)
    else:
        # Генерируем новую очередь через сервис ранжирования
        profile_ids = UserService.get_profile_for_ranking(user_id)
        cache_service.redis_client.setex(queue_key, 60, json.dumps(profile_ids))
    
    if not profile_ids:
        await update.message.reply_text("Нет больше анкет для показа.")
        return
    
    next_profile_id = profile_ids.pop(0)
    # Обновляем очередь в Redis (без следующей анкеты)
    cache_service.redis_client.setex(queue_key, 60, json.dumps(profile_ids))
    
    profile = db_session.query(Profile).get(next_profile_id)
    if not profile:
        await update.message.reply_text("Анкета не найдена.")
        return

    user = profile.user
    age = profile.age if hasattr(profile, 'age') else '?'
    text = f"{user.first_name}, {age} лет, г.{profile.city or 'не указан'}\n\n{profile.bio or ''}"

    # Кнопки лайк/дизлайк/выход
    keyboard = [
        [InlineKeyboardButton("❤️ Лайк", callback_data=f"like_{profile.id}"),
         InlineKeyboardButton("❌ Пропуск", callback_data=f"skip_{profile.id}"),
         InlineKeyboardButton("🚪 Выйти из поиска", callback_data="exit_feed")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Запись просмотра
    existing_view = db_session.query(ViewsHistory).filter_by(
        viewer_profile_id=viewer_profile.id,
        viewed_profile_id=profile.id
    ).first()
    if not existing_view:
        new_view = ViewsHistory(
            viewer_profile_id=viewer_profile.id,
            viewed_profile_id=profile.id
        )
        db_session.add(new_view)
        db_session.commit()

    # ---------- Отправка анкеты с фото ----------
    from bot.models.photo import Photo
    main_photo = db_session.query(Photo).filter_by(profile_id=profile.id, is_main=True).first()
    if main_photo:
        from bot.services.s3_service import S3Service
        if main_photo.s3_key:
            s3 = S3Service()
            photo_url = s3.get_photo_url(main_photo.s3_key)
            await update.message.reply_photo(
                photo=photo_url,
                caption=text,
                reply_markup=reply_markup
            )
        elif main_photo.file_id:
            await update.message.reply_photo(
                photo=main_photo.file_id,
                caption=text,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def feed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать следующую анкету (обработчик команды /feed и кнопки)"""
    await show_next_profile(update, context)

async def handle_feed_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    user_id = update.effective_user.id
    viewer_user = UserService.get_user_by_telegram_id(user_id)
    viewer_profile = UserService.get_user_profile(viewer_user.id)
    
    if data == "exit_feed":
        await query.edit_message_text("🚪 Вы вышли из режима просмотра анкет.")
        return
    
    action, profile_id = data.split('_')
    profile_id = int(profile_id)
    
    if action == 'like':
        process_like_async.delay(viewer_profile.id, profile_id)
        total_likes.inc()
        await query.edit_message_text("❤️ Вы поставили лайк!")
        await feed_command(update, context)
        return
    
    elif action == 'skip':
        MatchingService.add_dislike(viewer_profile.id, profile_id)
        await query.edit_message_text("❌ Вы пропустили анкету.")
        await feed_command(update, context)
        return
    
    # На всякий случай
    await query.edit_message_text("Неизвестное действие.")