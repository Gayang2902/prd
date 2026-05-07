from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.router import api_router
from app.api.v1.ws import router as ws_router
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.rate_limit import RateLimitMiddleware

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)

register_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(api_router)
app.include_router(ws_router)
