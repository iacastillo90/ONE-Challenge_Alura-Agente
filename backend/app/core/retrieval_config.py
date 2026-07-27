from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings


@dataclass
class RetrievalConfig:
    name: str = "default"
    top_k: int = 5
    score_threshold: float | None = None
    use_hybrid_search: bool = True
    hybrid_search_alpha: float = 0.7
    chunk_size: int = 512
    chunk_overlap: int = 64

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "top_k": self.top_k,
            "score_threshold": self.score_threshold,
            "use_hybrid_search": self.use_hybrid_search,
            "hybrid_search_alpha": self.hybrid_search_alpha,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RetrievalConfig:
        return cls(
            name=data.get("name", "custom"),
            top_k=data.get("top_k", 5),
            score_threshold=data.get("score_threshold"),
            use_hybrid_search=data.get("use_hybrid_search", True),
            hybrid_search_alpha=data.get("hybrid_search_alpha", 0.7),
            chunk_size=data.get("chunk_size", 512),
            chunk_overlap=data.get("chunk_overlap", 64),
        )

    @classmethod
    def from_settings(cls) -> RetrievalConfig:
        return cls(
            name="default",
            top_k=5,
            score_threshold=settings.retrieval_score_threshold,
            use_hybrid_search=settings.use_hybrid_search,
            hybrid_search_alpha=settings.hybrid_search_alpha,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )


DEFAULT_CONFIG = RetrievalConfig.from_settings()


BUILTIN_EXPERIMENTS: list[RetrievalConfig] = [
    RetrievalConfig(
        name="precision",
        top_k=3,
        score_threshold=0.6,
        hybrid_search_alpha=0.9,
    ),
    RetrievalConfig(
        name="recall",
        top_k=10,
        score_threshold=0.3,
        use_hybrid_search=True,
        hybrid_search_alpha=0.5,
    ),
    RetrievalConfig(
        name="vector_only",
        top_k=5,
        score_threshold=0.45,
        use_hybrid_search=False,
        hybrid_search_alpha=1.0,
    ),
    RetrievalConfig(
        name="hybrid_balanced",
        top_k=7,
        score_threshold=0.35,
        use_hybrid_search=True,
        hybrid_search_alpha=0.6,
    ),
]
