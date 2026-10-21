import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.api.v1 import auth, order, show
from app.database import AsyncSessionLocal
from app.services import seat_lock_service

CLEANUP_INTERVAL = 60  # 秒


async def _cleanup_loop() -> None:
    """启动即清理一次，之后每隔 60 秒清理一次过期锁。"""
    while True:
        try:
            async with AsyncSessionLocal() as db:
                count = await seat_lock_service.cleanup_expired_locks(db)
                if count:
                    print(f"[cleanup] 清理过期锁 {count} 条")
        except Exception as exc:  # 后台任务必须自己兜住异常，否则会静默死掉
            print(f"[cleanup] 出错: {exc}")
        await asyncio.sleep(CLEANUP_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="TickHub API", version="0.1.0", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(show.router)
app.include_router(order.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
