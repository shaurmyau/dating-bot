import logging
from datetime import datetime, date
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from bot.services.user_service import UserService
from bot.keyboards.reply_keyboards import get_gender_keyboard, get_search_gender_keyboard, get_cancel_keyboard, get_main_keyboard

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
(
    CHOICE,
    EDIT_GENDER,
    EDIT_BIRTH_DATE,
    EDIT_CITY,
    EDIT_BIO,
    EDIT_SEARCH_GENDER,
    EDIT_SEARCH_AGE_MIN,
    EDIT_SEARCH_AGE_MAX,
    EDIT_SEARCH_DISTANCE,
    EDIT_PHOTO 
) = range(10)

async def edit_profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало редактирования – показать меню выбора поля"""
    await update.message.reply_text(
        "✏️ Редактирование анкеты\n\n"
        "Выберите, что хотите изменить:\n"
        "1️⃣ Пол\n"
        "2️⃣ Дата рождения\n"
        "3️⃣ Город\n"
        "4️⃣ О себе\n"
        "5️⃣ Кого искать (пол)\n"
        "6️⃣ Минимальный возраст поиска\n"
        "7️⃣ Максимальный возраст поиска\n"
        "8️⃣ Расстояние поиска (км)\n\n"
        "9️⃣ Фото\n\n"
        "Введите номер (1-9) или /cancel для отмены.",
        reply_markup=get_main_keyboard()
    )
    return CHOICE

async def edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"edit_choice получил: {update.message.text}")
    """Обработка выбора пункта меню"""
    choice = update.message.text.strip()
    if choice == '1':
        await update.message.reply_text("Укажите ваш пол:", reply_markup=get_gender_keyboard())
        return EDIT_GENDER
    elif choice == '2':
        await update.message.reply_text(
            "Введите дату рождения в формате ДД.ММ.ГГГГ\nНапример: 15.05.1995",
            reply_markup=get_cancel_keyboard()
        )
        return EDIT_BIRTH_DATE
    elif choice == '3':
        await update.message.reply_text("Введите ваш город:", reply_markup=get_cancel_keyboard())
        return EDIT_CITY
    elif choice == '4':
        await update.message.reply_text(
            "Введите новое описание (максимум 500 символов):",
            reply_markup=get_cancel_keyboard()
        )
        return EDIT_BIO
    elif choice == '5':
        await update.message.reply_text("Кого вы хотите искать?", reply_markup=get_search_gender_keyboard())
        return EDIT_SEARCH_GENDER
    elif choice == '6':
        await update.message.reply_text("Минимальный возраст партнера (от 18 до 100):", reply_markup=get_cancel_keyboard())
        return EDIT_SEARCH_AGE_MIN
    elif choice == '7':
        await update.message.reply_text("Максимальный возраст партнера (от 18 до 100):", reply_markup=get_cancel_keyboard())
        return EDIT_SEARCH_AGE_MAX
    elif choice == '8':
        await update.message.reply_text("Максимальное расстояние поиска (км, от 1 до 500):", reply_markup=get_cancel_keyboard())
        return EDIT_SEARCH_DISTANCE
    elif choice == '9':
        await update.message.reply_text(
            "Отправьте новое фото для вашей анкеты.\n"
            "Оно заменит текущее главное фото.",
            reply_markup=get_cancel_keyboard()
        )
        return EDIT_PHOTO
    else:
        await update.message.reply_text("Пожалуйста, введите число от 1 до 8.")
        return CHOICE

async def process_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение пола"""
    if update.message.text == "Отмена":
        return await cancel_edit(update, context)
    gender_map = {"Мужской": "male", "Женский": "female", "Другой": "other"}
    if update.message.text not in gender_map:
        await update.message.reply_text("Пожалуйста, используйте кнопки.", reply_markup=get_gender_keyboard())
        return EDIT_GENDER
    UserService.update_profile(update.effective_user.id, gender=gender_map[update.message.text])
    await update.message.reply_text("✅ Пол обновлён!", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def process_birth_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение даты рождения"""
    if update.message.text == "Отмена":
        return await cancel_edit(update, context)
    try:
        birth_date = datetime.strptime(update.message.text, "%d.%m.%Y").date()
        # Проверка возраста
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        if age < 18:
            await update.message.reply_text("❌ Вам должно быть не меньше 18 лет.", reply_markup=get_cancel_keyboard())
            return EDIT_BIRTH_DATE
        if age > 100:
            await update.message.reply_text("❌ Укажите корректную дату.", reply_markup=get_cancel_keyboard())
            return EDIT_BIRTH_DATE
        UserService.update_profile(update.effective_user.id, birth_date=birth_date)
        await update.message.reply_text("✅ Дата рождения обновлена!", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Неверный формат. Используйте ДД.ММ.ГГГГ", reply_markup=get_cancel_keyboard())
        return EDIT_BIRTH_DATE

async def process_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение города"""
    if update.message.text == "Отмена":
        return await cancel_edit(update, context)
    city = update.message.text.strip()
    if len(city) < 2:
        await update.message.reply_text("Введите корректное название города.", reply_markup=get_cancel_keyboard())
        return EDIT_CITY
    UserService.update_profile(update.effective_user.id, city=city)
    await update.message.reply_text("✅ Город обновлён!", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def process_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение описания"""
    if update.message.text == "Отмена":
        return await cancel_edit(update, context)
    bio = update.message.text.strip()
    if len(bio) > 500:
        await update.message.reply_text("Описание не должно превышать 500 символов.", reply_markup=get_cancel_keyboard())
        return EDIT_BIO
    UserService.update_profile(update.effective_user.id, bio=bio)
    await update.message.reply_text("✅ Описание обновлено!", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def process_search_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение предпочтений по полу для поиска"""
    if update.message.text == "Отмена":
        return await cancel_edit(update, context)
    gender_map = {"Мужской": "male", "Женский": "female", "Любой": "any"}
    if update.message.text not in gender_map:
        await update.message.reply_text("Пожалуйста, используйте кнопки.", reply_markup=get_search_gender_keyboard())
        return EDIT_SEARCH_GENDER
    UserService.update_profile(update.effective_user.id, search_gender=gender_map[update.message.text])
    await update.message.reply_text("✅ Предпочтения по полу обновлены!", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def process_age_min(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение минимального возраста поиска"""
    if update.message.text == "Отмена":
        return await cancel_edit(update, context)
    try:
        age_min = int(update.message.text)
        if age_min < 18 or age_min > 100:
            await update.message.reply_text("Возраст должен быть от 18 до 100.", reply_markup=get_cancel_keyboard())
            return EDIT_SEARCH_AGE_MIN
        UserService.update_profile(update.effective_user.id, search_age_min=age_min)
        await update.message.reply_text("✅ Минимальный возраст поиска обновлён!", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Введите целое число.", reply_markup=get_cancel_keyboard())
        return EDIT_SEARCH_AGE_MIN

async def process_age_max(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение максимального возраста поиска"""
    if update.message.text == "Отмена":
        return await cancel_edit(update, context)
    try:
        age_max = int(update.message.text)
        if age_max < 18 or age_max > 100:
            await update.message.reply_text("Возраст должен быть от 18 до 100.", reply_markup=get_cancel_keyboard())
            return EDIT_SEARCH_AGE_MAX
        # Получим текущий минимум из БД, чтобы проверить
        user = UserService.get_user_by_telegram_id(update.effective_user.id)
        profile = UserService.get_user_profile(user.id)
        if age_max < profile.search_age_min:
            await update.message.reply_text(f"Максимальный возраст не может быть меньше минимального ({profile.search_age_min}).", reply_markup=get_cancel_keyboard())
            return EDIT_SEARCH_AGE_MAX
        UserService.update_profile(update.effective_user.id, search_age_max=age_max)
        await update.message.reply_text("✅ Максимальный возраст поиска обновлён!", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Введите целое число.", reply_markup=get_cancel_keyboard())
        return EDIT_SEARCH_AGE_MAX

async def process_distance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение расстояния поиска"""
    if update.message.text == "Отмена":
        return await cancel_edit(update, context)
    try:
        distance = int(update.message.text)
        if distance < 1 or distance > 500:
            await update.message.reply_text("Расстояние должно быть от 1 до 500 км.", reply_markup=get_cancel_keyboard())
            return EDIT_SEARCH_DISTANCE
        UserService.update_profile(update.effective_user.id, search_distance_km=distance)
        await update.message.reply_text("✅ Расстояние поиска обновлено!", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Введите целое число.", reply_markup=get_cancel_keyboard())
        return EDIT_SEARCH_DISTANCE

async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена редактирования"""
    await update.message.reply_text("Редактирование отменено.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def process_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение нового фото (замена существующего главного)"""
    if update.message.text == "Отмена":
        return await cancel_edit(update, context)
    
    if not update.message.photo:
        await update.message.reply_text(
            "Пожалуйста, отправьте фото (обычное изображение).",
            reply_markup=get_cancel_keyboard()
        )
        return EDIT_PHOTO
    
    from bot.models.photo import Photo
    from bot.models.database import db_session
    from bot.services.s3_service import S3Service
    
    user_id = update.effective_user.id
    user = UserService.get_user_by_telegram_id(user_id)
    profile = UserService.get_user_profile(user.id)
    if not profile:
        await update.message.reply_text("Профиль не найден.")
        return ConversationHandler.END
    
    # Скачиваем и загружаем в S3
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    file_bytes = await file.download_as_bytearray()
    s3 = S3Service()
    s3_key = s3.upload_photo(bytes(file_bytes), 'jpg')
    
    # Удаляем все старые фото пользователя
    db_session.query(Photo).filter_by(profile_id=profile.id).delete()
    
    # Сохраняем новое фото
    new_photo = Photo(
        profile_id=profile.id,
        s3_key=s3_key,
        file_id=photo.file_id,
        order_index=0,
        is_main=True
    )
    db_session.add(new_photo)
    db_session.commit()
    
    # Сброс кэша
    from bot.services.cache_service import CacheService
    CacheService().delete_cached_profile(profile.id)
    
    await update.message.reply_text(
        "✅ Фото обновлено!",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END