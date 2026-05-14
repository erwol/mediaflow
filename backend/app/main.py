from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import download, parse

app = FastAPI(title="mediaflow")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parse.router)
app.include_router(download.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
