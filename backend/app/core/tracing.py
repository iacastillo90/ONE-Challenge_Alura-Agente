import secrets
import time

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or secrets.token_hex(12)
        start = time.perf_counter()

        with logger.contextualize(request_id=request_id):
            logger.info(f"{request.method} {request.url.path} — incoming")

            response = await call_next(request)

            duration = time.perf_counter() - start
            logger.info(
                f"{request.method} {request.url.path} — {response.status_code} in {duration*1000:.0f}ms"
            )
            response.headers["X-Request-ID"] = request_id

        return response


class RequestContextLogger:
    def __init__(self):
        self._request_id: str = "system"

    def bind(self, request_id: str):
        self._request_id = request_id
        logger.debug(f"Context bound: request_id={request_id}")

    @property
    def request_id(self) -> str:
        return self._request_id


ctx = RequestContextLogger()
