#!/usr/bin/env python3
from telegram import Update
import logging
from bot.metrics import init_metrics
from config import config
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters
)
from bot.handlers.edit_profile import (
    edit_profile_start,
    edit_choice,
    process_gender,
    process_birth_date,
    process_city,
    process_bio,
    process_search_gender,
    process_age_min,
    process_age_max,
    process_distance,
    cancel_edit,
    process_photo,
    # Импортируем состояния
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
)
from bot.handlers.feed import feed_command, handle_feed_callback
from config import config
from bot.handlers.start import (
    start_command,
    handle_registration_confirmation,
    delete_account,
    confirm_delete_account,
    my_profile,
    my_chats,
    settings
)
from bot.handlers.registration import (
    registration_start,
    ask_gender,
    ask_age,
    ask_city,
    ask_bio,
    ask_photo,
    ask_search_gender,
    ask_search_age_min,
    ask_search_age_max,
    ask_search_distance,
    cancel_registration
)
# импортируем CallbackQueryHandler из telegram.ext
from telegram.ext import CallbackQueryHandler
from bot.states.registration_states import *
from bot.models.database import init_db
from bot.handlers.start import delete_account, confirm_delete_account

from bot.handlers.feed import feed_command

from bot.handlers.feed import handle_feed_callback

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO if not config.DEBUG else logging.DEBUG
)

logger = logging.getLogger(__name__)

def main() -> None:
    """Запуск бота"""
    # Инициализация базы данных
    init_db()
    logger.info("Database initialized")
   
    # Создание приложения
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("feed", feed_command))

    application.add_handler(CallbackQueryHandler(handle_feed_callback, pattern='^(like|skip)_'))
    
    application.add_handler(MessageHandler(filters.Regex('^👤 Моя анкета$'), my_profile))
    application.add_handler(MessageHandler(filters.Regex('^💬 Чаты$'), my_chats))
    application.add_handler(MessageHandler(filters.Regex('^⚙️ Настройки$'), settings))
    application.add_handler(MessageHandler(filters.Regex('^🔍 Смотреть анкеты$'), feed_command))
    application.add_handler(MessageHandler(filters.Regex('^Удалить аккаунт$'), delete_account))

    # Регистрация обработчика регистрации
    registration_handler = ConversationHandler(
        entry_points=[
            CommandHandler('register', registration_start),
            MessageHandler(
                filters.Regex('^✅ Да, начать регистрацию$'),
                registration_start
            )
        ],
        states={
            ASK_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_gender)],
            ASK_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            ASK_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_city)],
            ASK_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_bio)],
            ASK_PHOTO: [MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, ask_photo)],
            ASK_SEARCH_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_search_gender)],
            ASK_SEARCH_AGE_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_search_age_min)],
            ASK_SEARCH_AGE_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_search_age_max)],
            ASK_SEARCH_DISTANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_search_distance)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_registration),
            MessageHandler(filters.Regex('^Отмена$'), cancel_registration)
        ],
        name="registration_conversation",
        persistent=False
    )
    
    edit_conv = ConversationHandler(
        entry_points=[
            CommandHandler("edit_profile", edit_profile_start),
            MessageHandler(filters.Regex('^✏️ Редактировать анкету$'), edit_profile_start)
        ],
        states={
            CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_choice)],
            EDIT_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_gender)],
            EDIT_BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_birth_date)],
            EDIT_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_city)],
            EDIT_BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_bio)],
            EDIT_SEARCH_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_search_gender)],
            EDIT_SEARCH_AGE_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_age_min)],
            EDIT_SEARCH_AGE_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_age_max)],
            EDIT_SEARCH_DISTANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_distance)],
            EDIT_PHOTO: [MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, process_photo)],
        },
        fallbacks=[CommandHandler("cancel", cancel_edit)],
    )
    application.add_handler(edit_conv)

    application.add_handler(
        MessageHandler(
            filters.Regex('^(✅ Да, удалить аккаунт|❌ Нет, отменить)$'),
            confirm_delete_account
        )
    )   
    application.add_handler(registration_handler)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(
        MessageHandler(
            filters.Regex('^(✅ Да, начать регистрацию|❌ Нет, позже)$'),
            handle_registration_confirmation
        )
    )
    
    init_metrics(config.METRICS_PORT)
    
    # Запуск бота
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()