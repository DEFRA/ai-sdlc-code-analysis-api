from contextlib import asynccontextmanager
from logging import getLogger

from fastapi import FastAPI

from app.code_analysis.api.v1.code_analysis import router as code_analysis_router
from app.common.mongo import get_mongo_client
from app.common.tracing import TraceIdMiddleware
from app.health.router import router as health_router

logger = getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup
    client = await get_mongo_client()
    logger.info("MongoDB client connected")
    yield
    # Shutdown
    if client:
        await client.close()
        logger.info("MongoDB client closed")


app = FastAPI(lifespan=lifespan)

# Setup middleware
app.add_middleware(TraceIdMiddleware)

# Setup Routes
app.include_router(health_router)
app.include_router(code_analysis_router)
