import time

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency (seconds)",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

ACTIVE_REQUESTS = Gauge(
    "http_requests_active",
    "Currently active requests",
)

DOCUMENTS_UPLOADED = Counter(
    "documents_uploaded_total",
    "Total documents uploaded",
    ["status"],
)

DOCUMENTS_CHUNKS = Histogram(
    "documents_chunks_per_document",
    "Number of chunks per document",
    buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000),
)

LLM_REQUESTS = Counter(
    "llm_requests_total",
    "Total LLM requests by provider",
    ["provider", "status"],
)

LLM_LATENCY = Histogram(
    "llm_request_duration_seconds",
    "LLM request latency by provider",
    ["provider"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

TOKENS_CONSUMED = Counter(
    "llm_tokens_consumed_total",
    "Total tokens consumed (prompt + completion)",
    ["provider", "type"],
)

SESSION_COUNT = Gauge(
    "sessions_active_total",
    "Currently active sessions",
)

RETRIEVAL_QUERIES = Counter(
    "retrieval_queries_total",
    "Total retrieval queries",
    ["config_name", "cache_hit"],
)

RETRIEVAL_RESULTS = Histogram(
    "retrieval_results_per_query",
    "Number of results per retrieval query",
    buckets=(0, 1, 2, 3, 5, 10, 20, 50),
)

RETRIEVAL_LATENCY = Histogram(
    "retrieval_query_duration_seconds",
    "Retrieval query latency",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)

RETRIEVAL_SCORES = Histogram(
    "retrieval_similarity_scores",
    "Similarity scores of retrieved chunks",
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        ACTIVE_REQUESTS.inc()

        route = request.scope.get("route")
        endpoint = route.path if route else request.url.path

        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration = time.perf_counter() - start
            ACTIVE_REQUESTS.dec()

            status_code = response.status_code if response is not None else 500

            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=endpoint,
                status=status_code,
            ).inc()

            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=endpoint,
            ).observe(duration)


async def metrics_endpoint(request: Request) -> Response:
    if settings.api_key:
        api_key = request.headers.get("X-API-Key") or ""
        if api_key != settings.api_key:
            return Response(status_code=403, content="Forbidden")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
