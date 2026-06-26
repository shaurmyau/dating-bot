import json
from bot.services.cache_service import CacheService

def test_cache_profile(fake_redis):
    cache = CacheService()
    profile_data = {"id": 1, "name": "test"}
    cache.cache_profile(1, profile_data, ttl=60)
    cached = cache.get_cached_profile(1)
    assert cached == profile_data
    # Проверяем TTL (через fakeredis можем проверить время жизни)
    ttl = fake_redis.ttl("profile:1")
    assert 0 < ttl <= 60

def test_cache_ranking_queue(fake_redis):
    cache = CacheService()
    queue = [1,2,3]
    cache.cache_ranking_queue(123, queue, ttl=30)
    stored = fake_redis.get("ranking_queue:123")
    assert json.loads(stored) == queue