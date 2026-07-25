from app.core.config import settings
from app.main import app

# CORS is configured directly in main.py using FastAPI's built-in middleware.
# This module exists for future CORS-related utilities or dynamic updates.

ALLOWED_ORIGINS = settings.cors_origins
