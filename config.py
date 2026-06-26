import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Конфигурация приложения"""
    
    # Telegram Bot
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/dating_bot')
    
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Application
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Bot settings
    MAX_PHOTOS = 5
    MAX_BIO_LENGTH = 500
    
    PORT = int(os.getenv('PORT', 8443))
    
    # S3 / MinIO
    S3_ENDPOINT = os.getenv('S3_ENDPOINT', 'http://localhost:9000')
    S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY', 'minioadmin')
    S3_SECRET_KEY = os.getenv('S3_SECRET_KEY', 'minioadmin')
    S3_BUCKET = os.getenv('S3_BUCKET', 'dating-photos')
    S3_REGION = os.getenv('S3_REGION', 'us-east-1')
    S3_USE_SSL = os.getenv('S3_USE_SSL', 'false').lower() == 'true'
    
    # Metrics
    METRICS_PORT = int(os.getenv('METRICS_PORT', 8000))
    
config = Config()