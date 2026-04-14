import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.infrastructure.vector_engine import VectorEngine
from app.infrastructure.cache_repository import CacheRepository
from app.infrastructure.event_broker import EventBroker
from app.api.router import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch environment variables
REDIS_URL = os.getenv("REDIS_URL", "redis://redis_cache:6379")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka_broker:9092")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and teardown routines.
    Initializes standard infrastructure connections to be injected at the API layer.
    """
    logger.info("Initializing Vector Engine (loading model)...")
    app.state.vector_engine = VectorEngine()

    logger.info("Connecting to Redis Cache Engine...")
    app.state.cache_repo = CacheRepository(REDIS_URL)
    await app.state.cache_repo.connect()

    logger.info("Connecting to Kafka Topic Producer...")
    app.state.event_broker = EventBroker(KAFKA_BROKER)
    await app.state.event_broker.connect()

    logger.info("Gateway fully started successfully.")
    
    yield

    # Application Teardown gracefully disconnects TCP wrappers
    logger.info("Shutting down infrastructure connections...")
    await app.state.cache_repo.close()
    await app.state.event_broker.close()


app = FastAPI(title="v-route API Gateway", lifespan=lifespan)

# Register functional endpoints
app.include_router(router)
