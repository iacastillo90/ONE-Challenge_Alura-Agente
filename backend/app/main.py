from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.routes import chat, documents, health, providers
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting agent backend — log_level={settings.log_level}")
    yield
    logger.info("Shutting down agent backend")


app = FastAPI(
    title="ONE AI Agent",
    description="Agente inteligente con RAG, multi-provider LLM y orquestación",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(providers.router, prefix="/providers", tags=["providers"])
