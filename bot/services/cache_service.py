import redis
import json
from config import config

class CacheService:
    def __init__(self):
        self.redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)

    def cache_profile(self, profile_id: int, profile_data: dict, ttl=300):
        """Кэширует данные анкеты на 5 минут"""
        key = f"profile:{profile_id}"
        self.redis_client.setex(key, ttl, json.dumps(profile_data))

    def get_cached_profile(self, profile_id: int) -> dict | None:
        key = f"profile:{profile_id}"
        data = self.redis_client.get(key)
        return json.loads(data) if data else None

    def delete_cached_profile(self, profile_id: int):
        self.redis_client.delete(f"profile:{profile_id}")

    def cache_ranking_queue(self, user_id: int, profile_ids: list, ttl=60):
        key = f"ranking_queue:{user_id}"
        self.redis_client.setex(key, ttl, json.dumps(profile_ids))