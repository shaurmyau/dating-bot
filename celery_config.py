from dotenv import load_dotenv
import os

load_dotenv()

broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

beat_schedule = {
    'update-active-users': {
        'task': 'bot.tasks.update_active_users_metric',
        'schedule': 60.0,  # каждую минуту
    },
}