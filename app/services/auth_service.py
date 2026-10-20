import secrets

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories import user_repository
from app.utils.security import hash_password, verify_password


async def register(db: AsyncSession, username: str, password: str) -> User:
    """注册：查重名 → 哈希密码 → 写入数据库。"""
    existing = await user_repository.get_user_by_username(db, username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在",
        )

    password_hash = hash_password(password)
    return await user_repository.create_user(db, username, password_hash)


async def login(db: AsyncSession, username: str, password: str) -> str:
    """登录：校验密码 → 生成令牌 → 覆盖旧令牌 → 返回新令牌。"""
    user = await user_repository.get_user_by_username(db, username)

    # 故意不区分「用户不存在」和「密码错误」，防止账号枚举
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    token = secrets.token_urlsafe(32)
    await user_repository.save_token(db, user, token)
    return token
