from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger


class AppException(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class DocumentNotFoundError(AppException):
    def __init__(self, message: str):
        super().__init__(message, code="DOCUMENT_NOT_FOUND", status_code=404)


class DocumentProcessingError(AppException):
    def __init__(self, message: str):
        super().__init__(message, code="DOCUMENT_PROCESSING_ERROR", status_code=422)


class ProviderUnavailableError(AppException):
    def __init__(self, message: str = "Todos los proveedores LLM no están disponibles"):
        super().__init__(message, code="PROVIDER_UNAVAILABLE", status_code=503)


class ProviderRateLimitError(AppException):
    def __init__(self, message: str = "Límite de tasa del proveedor LLM excedido"):
        super().__init__(message, code="PROVIDER_RATE_LIMITED", status_code=429)


class ProviderAuthError(AppException):
    def __init__(self, message: str = "Error de autenticación del proveedor LLM"):
        super().__init__(message, code="PROVIDER_AUTH_ERROR", status_code=401)


class RAGException(AppException):
    def __init__(self, message: str = "Error en recuperación de documentos"):
        super().__init__(message, code="RAG_ERROR", status_code=500)


class ConfigurationError(AppException):
    def __init__(self, message: str):
        super().__init__(message, code="CONFIGURATION_ERROR", status_code=500)


class TokenLimitError(AppException):
    def __init__(self, message: str = "Límite de tokens excedido"):
        super().__init__(message, code="TOKEN_LIMIT_EXCEEDED", status_code=413)


class StorageError(AppException):
    def __init__(self, message: str):
        super().__init__(message, code="STORAGE_ERROR", status_code=500)


class SessionNotFoundError(AppException):
    def __init__(self, message: str):
        super().__init__(message, code="SESSION_NOT_FOUND", status_code=404)


async def global_exception_handler(request: Request, exc: AppException):
    logger.warning(f"{exc.code} ({exc.status_code}): {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "Error interno del servidor"}},
    )
