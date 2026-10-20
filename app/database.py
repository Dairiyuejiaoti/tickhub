from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """所有表模型的基类，SQLAlchemy 通过它收集表结构。"""


engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,      # 开发时打印 SQL，能看清 ORM 到底发了什么
    pool_pre_ping=True,       # 取连接前先探活，避免用到被 MySQL 断掉的死连接
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,   # commit 后仍能读对象属性，否则会再查一次库
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：每个请求一个会话，用完自动关闭。"""
    async with AsyncSessionLocal() as session:
        yield session
