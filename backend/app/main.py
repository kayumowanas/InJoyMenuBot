from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.auth import verify_api_key
from app.database import init_db
from app.routers import admins
from app.routers import menu
from app.settings import settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(
    menu.router,
    prefix="/menu",
    tags=["menu"],
    dependencies=[Depends(verify_api_key)],
)

app.include_router(
    admins.router,
    prefix="/admins",
    tags=["admins"],
    dependencies=[Depends(verify_api_key)],
)
