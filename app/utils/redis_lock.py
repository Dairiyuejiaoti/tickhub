"""基于 Redis 的分布式锁（SET NX EX + Lua 安全释放）。

正确性要点：
1. 加锁用 SET key value NX EX，一条命令原子完成"不存在才设置 + 设置过期"；
2. value 用唯一 token，防止锁过期后误删别人的锁；
3. 释放用 Lua 脚本"比较 token 再删除"，保证原子；
4. Redis 不可用时降级为无锁，由数据库唯一约束兜底。
"""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from redis.exceptions import RedisError

from app.cache import redis

_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""


class LockBusy(Exception):
    """锁已被其他请求持有。"""


@asynccontextmanager
async def redis_lock(key: str, ttl: int = 10) -> AsyncIterator[str | None]:
    """获取一把 Redis 锁。

    Args:
        key: 锁的键，例如 f"seat:lock:{seat_id}"
        ttl: 锁自动过期秒数（防止进程崩溃导致死锁）

    Raises:
        LockBusy: 锁已被其他请求持有
    """
    token = uuid.uuid4().hex

    try:
        acquired = await redis.set(key, token, nx=True, ex=ttl)
    except RedisError:
        yield None          # 降级：Redis 故障时不阻塞业务，交给数据库约束兜底
        return

    if not acquired:
        raise LockBusy(key)

    try:
        yield token
    finally:
        try:
            await redis.eval(_RELEASE_SCRIPT, 1, key, token)
        except RedisError:
            pass            # 释放失败也没事，TTL 会自动兜底
