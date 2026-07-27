from __future__ import annotations

from typing import Any

from loguru import logger
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import Sampler, TraceIdRatioBased
from opentelemetry.trace import Span, Status, StatusCode

from app.core.config import settings


def setup_otel(app: Any = None) -> bool:
    if not settings.otel_enabled:
        logger.info("OpenTelemetry disabled by config")
        return False

    resource = Resource.create({
        "service.name": settings.otel_service_name,
        "service.version": "2.0.0",
        "deployment.environment": "production" if "prod" in settings.log_level.lower() else "development",
    })

    sampler: Sampler = (
        TraceIdRatioBased(settings.otel_sample_rate) if settings.otel_sample_rate < 1.0
        else trace.sampling.ALWAYS_ON
    )

    provider = TracerProvider(resource=resource, sampler=sampler)

    headers: dict[str, str] = {}
    if settings.otel_exporter_otlp_headers:
        for pair in settings.otel_exporter_otlp_headers.split(","):
            k, _, v = pair.partition("=")
            headers[k.strip()] = v.strip()

    exporter = OTLPSpanExporter(
        endpoint=settings.otel_exporter_otlp_endpoint,
        headers=headers or None,
    )

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    if app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            FastAPIInstrumentor.instrument_app(app)
        except Exception as e:
            logger.warning(f"FastAPI auto-instrumentation failed: {e}")

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        HTTPXClientInstrumentor().instrument()
    except Exception as e:
        logger.warning(f"httpx auto-instrumentation failed: {e}")

    logger.info(f"OpenTelemetry initialized — exporting to {settings.otel_exporter_otlp_endpoint}")
    return True


def shutdown_otel() -> None:
    try:
        provider = trace.get_tracer_provider()
        if isinstance(provider, TracerProvider):
            provider.shutdown()
            logger.info("OpenTelemetry shut down")
    except Exception as e:
        logger.warning(f"OpenTelemetry shutdown error: {e}")


def get_tracer(name: str = "one-ai-agent") -> trace.Tracer:
    return trace.get_tracer(name)


_tracer = get_tracer()


def start_span(name: str, attributes: dict[str, Any] | None = None) -> Span:
    span = _tracer.start_span(name)
    if attributes:
        span.set_attributes(attributes)
    return span


def end_span(span: Span, error: Exception | None = None) -> None:
    if error is not None:
        span.set_status(Status(StatusCode.ERROR, str(error)))
        span.record_exception(error)
    else:
        span.set_status(Status(StatusCode.OK))
    span.end()
