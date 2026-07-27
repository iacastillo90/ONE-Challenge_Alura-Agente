import sys

from loguru import logger


def setup_json_logging():
    logger.remove(0)
    logger.add(
        "logs/agent.json",
        format="{time} | {level} | {extra[request_id]: >16} | {name}:{function} | {message}",
        rotation="100 MB",
        retention=7,
        serialize=True,
    )
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[request_id]: >16}</cyan> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True,
    )
    logger.add(
        sys.stderr,
        format="<red>{time:HH:mm:ss}</red> | <level>{level: <8}</level> | <cyan>{extra[request_id]: >16}</cyan> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="WARNING",
        colorize=True,
    )


def get_request_id(request):
    return request.headers.get("X-Request-ID", "unknown")
