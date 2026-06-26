import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from bot.services.user_service import UserService
from bot.keyboards.reply_keyboards import get_main_keyboard, get_cancel_keyboard
from bot.handlers.edit_profile import edit_profile_start
from bot.models.database import db_session

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /start
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
    """
    user = update.effective_user
    
    # Сохраняем данные пользователя в контексте для регистрации
    context.user_data['telegram_id'] = user.id
    context.user_data['username'] = user.username
    context.user_data['first_name'] = user.first_name
    context.user_data['last_name'] = user.last_name
    
    # Получаем или создаем пользователя в БД
    db_user = UserService.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Проверяем, зарегистрирован ли пользователь
    is_registered = UserService.is_user_registered(user.id)
    
    if is_registered:
        # Пользователь уже зарегистрирован
        welcome_text = (
            f"С возвращением, {user.first_name}! 👋\n\n"
            f"Вы уже зарегистрированы в нашем дейтинг-боте.\n"
            f"Используйте кнопки меню для навигации:"
        )
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_main_keyboard()
        )
    else:
        # Новый пользователь - начинаем регистрацию
        welcome_text = (
            f"Привет, {user.first_name}! 👋\n\n"
            f"Добро пожаловать в дейтинг-бот!\n\n"
            f"Для начала работы нам нужно создать вашу анкету. "
            f"Это займет всего пару минут.\n\n"
            f"Готовы начать регистрацию?"
        )

        keyboard = [
            ["✅ Да, начать регистрацию"],
            ["❌ Нет, позже"]
        ]
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        )
        
        # Сохраняем состояние ожидания ответа о начале регистрации
        context.user_data['awaiting_registration_confirmation'] = True

async def handle_registration_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик подтверждения начала регистрации
    """
    user_response = update.message.text
    user = update.effective_user
    
    if user_response == "✅ Да, начать регистрацию":
        # Переходим к регистрации
        from bot.handlers.registration import registration_start
        await registration_start(update, context)
    elif user_response == "❌ Нет, позже":
        await update.message.reply_text(
            "Хорошо! Вы всегда можете начать регистрацию позже с помощью команды /register",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.pop('awaiting_registration_confirmation', None)
    else:
        await update.message.reply_text(
            "Пожалуйста, используйте кнопки для выбора.",
            reply_markup=ReplyKeyboardMarkup(
                [["✅ Да, начать регистрацию"], ["❌ Нет, позже"]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        
async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Удаление аккаунта пользователя
    """
    user = update.effective_user
    telegram_id = user.id
    
    # Получаем пользователя из БД
    db_user = UserService.get_user_by_telegram_id(telegram_id)
    
    if not db_user:
        await update.message.reply_text(
            "❌ Аккаунт не найден.\n"
            "Возможно, вы еще не зарегистрированы. Используйте /start для регистрации."
        )
        return
    
    # Запрашиваем подтверждение
    keyboard = [
        ["✅ Да, удалить аккаунт"],
        ["❌ Нет, отменить"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "⚠️ ВНИМАНИЕ! ⚠️\n\n"
        "Вы действительно хотите удалить свой аккаунт?\n\n"
        "Это действие НЕОБРАТИМО:\n"
        "• Ваша анкета будет удалена\n"
        "• Все ваши фотографии будут удалены\n"
        "• Все лайки и дизлайки будут стерты\n"
        "• Все чаты будут удалены\n"
        "• Ваши сообщения будут удалены\n\n"
        "Подтвердите удаление:",
        reply_markup=reply_markup
    )
    
    # Сохраняем состояние ожидания подтверждения
    context.user_data['awaiting_delete_confirmation'] = True

async def confirm_delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Подтверждение удаления аккаунта
    """
    answer = update.message.text
    user = update.effective_user  # Это объект Telegram User
    
    if answer == "✅ Да, удалить аккаунт":
        # Удаляем аккаунт - передаем telegram_id
        success = UserService.delete_user_account(user.id)  # user.id - это telegram_id
        
        if success:
            await update.message.reply_text(
                "✅ Ваш аккаунт успешно удален.\n\n"
                "Если захотите вернуться, просто отправьте команду /start для создания новой анкеты.",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text(
                "❌ Произошла ошибка при удалении аккаунта.\n"
                "Пожалуйста, попробуйте позже или обратитесь к администратору."
            )
    else:
        from bot.keyboards.reply_keyboards import get_main_keyboard
        await update.message.reply_text(
            "❌ Удаление аккаунта отменено.",
            reply_markup=get_main_keyboard()
        )
    
    # Очищаем состояние
    context.user_data.pop('awaiting_delete_confirmation', None)
    
async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать свою анкету с фото"""
    user_id = update.effective_user.id
    user = UserService.get_user_by_telegram_id(user_id)
    if not user:
        await update.message.reply_text("Вы не зарегистрированы. Напишите /start")
        return
    
    profile = UserService.get_user_profile(user.id)
    if not profile or not profile.is_completed:
        await update.message.reply_text("Анкета не заполнена. Начните регистрацию через /start")
        return
    
    # Собираем информацию
    age = profile.age if hasattr(profile, 'age') else 'не указан'
    text = (
        f"👤 <b>Ваша анкета</b>\n\n"
        f"Имя: {user.first_name or 'не указано'}\n"
        f"Пол: {profile.gender}\n"
        f"Возраст: {age}\n"
        f"Город: {profile.city or 'не указан'}\n"
        f"О себе: {profile.bio or 'не указано'}\n\n"
        f"Предпочтения:\n"
        f"Ищу: {profile.search_gender}\n"
        f"Возраст: {profile.search_age_min}-{profile.search_age_max}\n"
        f"Расстояние: {profile.search_distance_km} км"
    )
    
    from bot.models.photo import Photo
    main_photo = db_session.query(Photo).filter_by(profile_id=profile.id, is_main=True).first()
    
    if main_photo and main_photo.s3_key:
        from bot.services.s3_service import S3Service
        s3 = S3Service()
        photo_url = s3.get_photo_url(main_photo.s3_key)
        await update.message.reply_photo(photo=photo_url, caption=text, parse_mode='HTML')
    else:
        await update.message.reply_text(text, parse_mode='HTML')

async def my_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список чатов (пока заглушка)"""
    await update.message.reply_text("💬 Список чатов появится здесь, когда у вас будут взаимные лайки.")

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройки (заглушка)"""
    await update.message.reply_text(
        "⚙️ Настройки пока в разработке.\n"
        "Вы можете удалить аккаунт командой /delete_account"
    )