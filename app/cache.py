"""Redis 客户端与 JSON 缓存的最小封装。

为什么要封装一层：
1. 整个项目共用一个连接池，避免到处 Redis.from_url 建新连接；
2. 统一用 JSON 序列化，业务代码不用关心 bytes/str 转换；
3. 以后要加 key 前缀、缓存命中率统计，只改这一处。
"""

import json
from typing import Any

from redis.asyncio import Redis

from app.config import settings

# decode_responses=True：取出来直接是 str，不用手动 decode
redis: Redis = Redis.from_url(settings.redis_url, decode_responses=True)


async def get_json(key: str) -> Any | None:
    """读缓存；不存在返回 None。"""
    raw = await redis.get(key)
    return json.loads(raw) if raw is not None else None


async def set_json(key: str, value: Any, ttl: int) -> None:
    """写缓存并设置过期秒数。"""
    await redis.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)


async def delete(key: str) -> None:
    """删除缓存（写操作后调用，保证下次读到新数据）。"""
    await redis.delete(key)


async def close() -> None:
    """关闭连接池，服务退出时调用。"""
    await redis.aclose()
