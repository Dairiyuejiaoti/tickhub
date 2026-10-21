"""pytest 公共装置：测试数据库、Redis 隔离、HTTP 客户端。

关键点：环境变量必须在 import app 之前设置，因为 Settings 是模块级单例。
"""

import os

os.environ["DATABASE_URL"] = (
    "mysql+aiomysql://root:123456@127.0.0.1:3307/tickhub_test?charset=utf8mb4"
)
os.environ["REDIS_URL"] = "redis://127.0.0.1:6379/1"  # 用 1 号库，不碰开发的 0 号库
os.environ["DEBUG"] = "false"

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.cache import redis
from app.database import Base, engine
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def fresh_database():
    """每个用例前：确保测试库存在 → 重建表 → 清空测试 Redis。"""
    admin_url = os.environ["DATABASE_URL"].rsplit("/", 1)[0]
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        await conn.execute(
            text("CREATE DATABASE IF NOT EXISTS tickhub_test CHARACTER SET utf8mb4")
        )
    await admin_engine.dispose()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    await redis.flushdb()
    yield


@pytest_asyncio.fixture
async def client():
    """直连 ASGI 应用，不起真实端口。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
