import redis
import json
import os

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = 6379
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "redis_password")

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True
)

CACHE_TTL = 60 * 60 * 24  # 24 hours


def get_cached_asteroid(name: str):
    key = f"asteroid:{name.lower()}"
    data = r.get(key)
    return json.loads(data) if data else None


def set_cached_asteroid(name: str, payload: dict):
    key = f"asteroid:{name.lower()}"
    r.setex(key, CACHE_TTL, json.dumps(payload))
