class AgentException(Exception):
    """Base exception for the agent system."""


class ProviderException(AgentException):
    """Base exception for LLM provider errors."""


class ProviderRateLimitError(ProviderException):
    """Provider rate limit exceeded."""


class ProviderTimeoutError(ProviderException):
    """Provider request timed out."""


class ProviderAuthError(ProviderException):
    """Provider authentication failed."""


class ProviderUnavailableError(ProviderException):
    """Provider is not available."""


class RAGException(AgentException):
    """Base exception for RAG errors."""


class DocumentNotFoundError(RAGException):
    """Document not found in the store."""


class DocumentProcessingError(RAGException):
    """Error processing document."""


class EmbeddingError(RAGException):
    """Error generating embeddings."""


class MemoryException(AgentException):
    """Base exception for memory errors."""


class SessionNotFoundError(MemoryException):
    """Session not found."""
