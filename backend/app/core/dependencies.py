from fastapi import Depends

from app.core.config import Settings, settings as app_settings


async def get_settings() -> Settings:
    return app_settings
