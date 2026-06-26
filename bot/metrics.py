from prometheus_client import Counter, Gauge, Histogram, start_http_server
import logging
from functools import wraps
import time

logger = logging.getLogger(__name__)

# Определение метрик
active_users = Gauge('active_users', 'Number of users with completed profile')
total_likes = Counter('total_likes', 'Total number of likes given')
total_dislikes = Counter('total_dislikes', 'Total number of dislikes given')
total_matches = Counter('total_matches', 'Total number of matches created')
total_messages = Counter('total_messages', 'Total messages sent')  # задел на будущее
api_request_duration = Histogram('api_request_duration_seconds', 'Duration of API requests', ['handler'])

# Функция для запуска HTTP-сервера метрик
def init_metrics(port=8000):
    try:
        start_http_server(port)
        logger.info(f"Metrics server started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")

def measure_duration(handler_name):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start
                api_request_duration.labels(handler=handler_name).observe(duration)
        return wrapper
    return decorator