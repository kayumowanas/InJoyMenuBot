import uvicorn

from app.settings import settings


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.address,
        port=settings.port,
        reload=settings.reload,
    )
