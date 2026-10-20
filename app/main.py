from fastapi import FastAPI

from app.api.v1 import auth

app = FastAPI(title="TickHub API", version="0.1.0")

app.include_router(auth.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
