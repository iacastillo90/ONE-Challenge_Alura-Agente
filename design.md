# Design.md — Diseño Técnico de Arquitectura

## Challenge ONE AI FOR TECH — Alura Latam

---

## 1. Arquitectura General del Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
 │                        DNS / Nginx (producción)                      │
 └─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
            ┌───────▼───────┐             ┌─────────▼──────────┐
            │   Frontend    │             │    Backend API      │
            │   React 19    │ ◄─SSE─►     │    FastAPI          │
            │   Tailwind    │   HTTP      │    Uvicorn          │
            │   Vite        │             │    :8000            │
            └───────┬───────┘             └─────────┬──────────┘
                    │                               │
                    │                     ┌─────────▼──────────┐
                    │                     │   Vector Store      │
                    │                     │   ChromaDB/Qdrant   │
                    │                     │   :8001/:6333       │
                    │                     └─────────────────────┘
                    │
            ┌───────▼───────┐
            │    n8n         │  (opcional)
            │    :5678       │
            └───────────────┘
```

### 1.1 Diagrama de Flujo — Consulta de Chat

```
Usuario                 Frontend                Backend                 Vector Store            LLM Provider
   │                       │                       │                       │                      │
   │   Escribe pregunta    │                       │                       │                      │
   │──────────────────────►│                       │                       │                      │
   │                       │  POST /chat (SSE)     │                       │                      │
   │                       │──────────────────────►│                       │                      │
   │                       │                       │                       │                      │
   │                       │                       │  Embed pregunta       │                      │
   │                       │                       │──────────────────────►│                      │
   │                       │                       │  similarity_search    │                      │
   │                       │                       │◄──────────────────────│                      │
   │                       │                       │                       │                      │
   │                       │                       │  Construir prompt     │                      │
   │                       │                       │  con contexto         │                      │
   │                       │                       │                       │                      │
   │                       │                       │  Chequear salud       │                      │
   │                       │                       │──────────────────────────────────────────────►│
   │                       │                       │◄──────────────────────────────────────────────│
   │                       │                       │                       │                      │
   │                       │                       │  Stream respuesta     │                      │
   │                       │                       │◄──────────────────────────────────────────────│
   │                       │   SSE: token chunks   │                       │                      │
   │                       │◄──────────────────────│                       │                      │
   │                       │                       │                       │                      │
   │   Renderiza tokens    │                       │                       │                      │
   │◄──────────────────────│                       │                       │                      │
   │                       │                       │                       │                      │
```

---

## 2. Componentes del Backend

### 2.1 Capa API (`backend/app/api/`)

#### 2.1.1 Routes

| Route | Método | Handler | Descripción |
|-------|--------|---------|-------------|
| `/chat` | POST | `chat_handler` | Acepta `{ message: str, session_id: str }`, retorna SSE stream |
| `/documents/upload` | POST | `upload_handler` | Multipart form, acepta PDF/CSV, inicia ingesta async |
| `/documents/{id}` | DELETE | `delete_handler` | Elimina documento y chunks asociados |
| `/documents` | GET | `list_handler` | Lista documentos con metadata (fecha, tamaño, estado) |
| `/providers` | GET | `list_providers_handler` | Lista providers con estado actual |
| `/providers/switch` | POST | `switch_provider_handler` | Cambia provider activo para la sesión |
| `/health` | GET | `health_handler` | Retorna estado del sistema y sus dependencias |

**Ejemplo de Request/Response — Chat Streaming:**

```python
# Request
POST /chat
Content-Type: application/json
{
    "message": "¿Cuál es el propósito del documento?",
    "session_id": "abc-123"
}

# Response (SSE stream)
event: token
data: {"token": "El", "done": false}

event: token
data: {"token": "propósito", "done": false}

event: token
data: {"token": "principal", "done": false}

...

event: done
data: {
    "full_response": "El propósito principal del documento es...",
    "sources": [
        {
            "document_name": "manual.pdf",
            "chunk": "Fragmento relevante...",
            "score": 0.92
        }
    ]
}
```

#### 2.1.2 Middleware

- **CORSMiddleware**: Permite origen `http://localhost:5173` en desarrollo, configurable via `CORS_ORIGINS`.
- **RateLimitMiddleware**: Limita requests por IP (100 req/min por defecto) usando token bucket.
- **RequestLoggingMiddleware**: Logea método, path, status code, duración.

### 2.2 Capa Core (`backend/app/core/`)

#### 2.2.1 Config (`config.py`)

Usa **Pydantic Settings** v2 para cargar configuración desde `.env`:

```python
class Settings(BaseSettings):
    # LLM Providers
    gemini_api_key: str = ""
    groq_api_key: str = ""
    deepseek_api_key: str = ""
    openai_compatible_api_key: str = ""
    openai_compatible_base_url: str = ""

    # Vector Store
    vector_store_type: Literal["chroma", "qdrant"] = "chroma"
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    # Embeddings
    embedding_provider: Literal["local", "api"] = "local"
    embedding_model: str = "all-MiniLM-L6-v2"

    # Backend
    log_level: str = "INFO"
    max_tokens: int = 4096
    temperature: float = 0.7
    system_prompt_path: str = "./prompts/system.txt"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

#### 2.2.2 Excepciones (`exceptions.py`)

Jerarquía de excepciones personalizadas:

```
AgentException (base)
├── ProviderException
│   ├── ProviderRateLimitError
│   ├── ProviderTimeoutError
│   ├── ProviderAuthError
│   └── ProviderUnavailableError
├── RAGException
│   ├── DocumentNotFoundError
│   ├── DocumentProcessingError
│   └── EmbeddingError
└── MemoryException
    └── SessionNotFoundError
```

#### 2.2.3 Dependencias (`dependencies.py`)

Inyección de dependencias vía `Depends` de FastAPI:

```python
async def get_settings() -> Settings:
    return Settings()

async def get_vector_store(settings: Settings = Depends(get_settings)) -> VectorStore:
    ...

async def get_embedding_provider(settings: Settings = Depends(get_settings)) -> EmbeddingProvider:
    ...

async def get_provider_router(settings: Settings = Depends(get_settings)) -> ProviderRouter:
    ...

async def get_chat_service(
    router: ProviderRouter = Depends(get_provider_router),
    vector_store: VectorStore = Depends(get_vector_store),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
) -> ChatService:
    ...
```

### 2.3 Capa LLM (`backend/app/llm/`)

#### 2.3.1 BaseProvider (`base.py`)

```python
class BaseProvider(ABC):
    name: str
    model: str
    priority: int

    @abstractmethod
    async def check_health(self) -> ProviderHealth:
        """Verifica si el provider está operativo y tiene cuota disponible."""
        ...

    @abstractmethod
    async def generate_stream(
        self, messages: list[Message], max_tokens: int, temperature: float
    ) -> AsyncGenerator[TokenEvent, None]:
        """Genera respuesta en streaming."""
        ...
```

#### 2.3.2 ProviderRouter (`router.py`)

El `ProviderRouter` es el cerebro del multi-provider:

```python
class ProviderRouter:
    """
    Orquesta la selección y failover de providers.

    Algoritmo:
    1. Obtener lista de providers ordenados por prioridad.
    2. Para cada provider en orden:
       a. Check health: si no responde o rate limited, pasar al siguiente.
       b. Enviar request.
       c. Si éxito: retornar stream.
       d. Si error: registrar fallo, pasar al siguiente.
    3. Si todos fallan: retornar error unificado.
    """
    providers: list[BaseProvider]
    active_provider: str | None  # provider forzado por usuario
    fallback_strategy: FallbackStrategy
```

**Estrategias de Fallback:**

- `circuit_breaker`: Si un provider falla N veces seguidas (default: 3), se marca como `degraded` por T segundos (default: 60).
- `exponential_backoff`: Reintentos con backoff exponencial (1s, 2s, 4s, max 8s) antes de pasar al siguiente provider.
- `concurrent_health_check`: Cada 30 segundos, verifica salud de todos los providers en background.

#### 2.3.3 Providers

**GeminiProvider:**

```python
class GeminiProvider(BaseProvider):
    name = "google-gemini"
    model = "gemini-2.0-flash"  # modelo gratuito
    priority = 1

    # Usa google-generativeai SDK
    # Rate limit: 60 req/min (tier gratuito)
    # Timeout: 30s
```

**GroqProvider:**

```python
class GroqProvider(BaseProvider):
    name = "groq"
    model = "llama-3.3-70b-versatile"
    priority = 2

    # Usa openai-compatible SDK (groq.openai.com)
    # Rate limit: 30 req/min, 6000 tokens/min (tier gratuito)
    # Timeout: 30s
```

**DeepSeekProvider:**

```python
class DeepSeekProvider(BaseProvider):
    name = "deepseek"
    model = "deepseek-chat"
    priority = 3

    # Usa openai-compatible SDK (api.deepseek.com)
    # Pago por uso (~$0.14/M tokens)
    # Timeout: 60s
```

**OpenAICompatibleProvider:**

```python
class OpenAICompatibleProvider(BaseProvider):
    name = "openai-compatible"
    model = ""  # configurable
    priority = 4

    # Usa openai SDK con base_url configurable
    # Ideal para OpenRouter, Together, vLLM, etc.
    # Timeout: 60s
```

### 2.4 Capa RAG (`backend/app/rag/`)

#### 2.4.1 Pipeline de Ingesta

```
PDF/CSV ──► Loader ──► Splitter ──► Embedding ──► Vector Store
                │            │
           Extrae texto  Chunks semánticos
           (PyMuPDF,     (512 tokens,
            csv.DictReader)  64 overlap)
```

**Loader:**

| Formato | Librería | Estrategia |
|---------|----------|------------|
| PDF | `PyMuPDF` (fitz) | Extracción página por página con metadata |
| CSV | `csv` + `pandas` | Cada fila se concatena con encabezados como texto |
| PDF escaneado | `pytesseract` + `pdf2image` | OCR opcional (requiere Tesseract instalado) |

**Splitter (Chunking Semántico):**

```python
class SemanticChunker:
    """
    Divide texto en chunks respetando límites naturales.

    Algoritmo:
    1. Divide por párrafos (\n\n).
    2. Si un párrafo excede chunk_size, usa RecursiveCharacterTextSplitter
       con separadores: ["\n\n", "\n", ".", "?", "!", " ", ""].
    3. Aplica overlap entre chunks consecutivos.
    """
    chunk_size: int = 512    # tokens (aproximado)
    chunk_overlap: int = 64   # tokens
```

**Processor:**

```python
class IngestionProcessor:
    """
    Orquesta el pipeline completo de ingesta.

    Flujo:
    1. Validar archivo (extensión, tamaño, MIME type).
    2. Cargar y extraer texto (Loader).
    3. Dividir en chunks (Splitter).
    4. Generar embeddings (EmbeddingProvider).
    5. Almacenar en vector store con metadata.
    6. Registrar documento en metadata store.
    """
```

#### 2.4.2 Retrieval

**Retriever:**

```python
class Retriever:
    """
    Búsqueda semántica con pipeline de retrieval-augmented generation.

    Algoritmo:
    1. Embed la pregunta del usuario.
    2. similarity_search en vector store (top_k=5).
    3. (Opcional) Re-ranking con CrossEncoder.
    4. Formatear contexto para el prompt.
    """
    top_k: int = 5
    score_threshold: float = 0.3  # mínimo de similitud
```

**Reranker (opcional):**

```python
class CrossEncoderReranker:
    """
    Re-ranking usando CrossEncoder (modelo ligero: ms-marco-MiniLM-L-6-v2).

    Flujo:
    1. Recibe query + lista de chunks candidates.
    2. Calcula score query-chunk con CrossEncoder.
    3. Re-ordena por score descendente.
    4. Retorna top_k reranked.
    """
```

#### 2.4.3 Embeddings

**EmbeddingProvider (Abstract):**

```python
class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    async def embed_query(self, query: str) -> list[float]:
        ...
```

**LocalEmbeddingProvider (default):**

```python
class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Usa sentence-transformers con modelo local.
    - Modelo: all-MiniLM-L6-v2 (384 dimensiones)
    - Cache: ~80MB RAM
    - Velocidad: ~100 textos/segundo (CPU)
    """
```

**APIEmbeddingProvider:**

```python
class APIEmbeddingProvider(EmbeddingProvider):
    """
    Usa API de Gemini para embeddings.
    - Modelo: text-embedding-004
    - Útil cuando se necesita mayor calidad.
    - Dependencia de API key.
    """
```

#### 2.4.4 Vector Store

**VectorStore (Abstract):**

```python
class VectorStore(ABC):
    @abstractmethod
    async def add_texts(self, texts: list[str], embeddings: list[list[float]], metadatas: list[dict]) -> list[str]:
        ...

    @abstractmethod
    async def similarity_search(self, query_embedding: list[float], k: int = 5) -> list[Document]:
        ...

    @abstractmethod
    async def delete_document(self, document_id: str) -> None:
        ...

    @abstractmethod
    async def get_collection_stats(self) -> CollectionStats:
        ...
```

**ChromaVectorStore (default para desarrollo):**

```python
class ChromaVectorStore(VectorStore):
    """
    ChromaDB en modo persistente (datos en ./chroma_data/).
    - Sin dependencias externas.
    - Persistencia en disco automática.
    - Colecciones: por documento para fácil eliminación.
    """
```

**QdrantVectorStore (producción):**

```python
class QdrantVectorStore(VectorStore):
    """
    Qdrant como servicio Docker.
    - Mayor rendimiento que ChromaDB.
    - Soporte para filtrado avanzado.
    - Recomendado para >100k chunks.
    """
```

### 2.5 Memoria Conversacional (`backend/app/memory/`)

```python
class ChatHistoryManager:
    """
    Gestión de memoria conversacional por sesión.

    Almacenamiento: SQLite (local) / Redis (producción).
    Estructura por sesión:
    {
        "session_id": str,
        "messages": [
            {"role": "user", "content": "...", "timestamp": "..."},
            {"role": "assistant", "content": "...", "timestamp": "..."},
        ],
        "max_history": 10  # últimos N intercambios
    }

    Estrategia de truncamiento:
    - Mantener últimos N intercambios (default: 10).
    - Si el total excede MAX_TOKENS_HISTORY (default: 2048),
      resumir los más antiguos.
    """
```

### 2.6 Servicios (`backend/app/services/`)

#### 2.6.1 ChatService

```python
class ChatService:
    """
    Orquesta el flujo completo de chat.

    1. Recibe message + session_id.
    2. Embed la pregunta.
    3. Recupera contexto relevante (Retriever).
    4. Obtiene historial de la sesión.
    5. Construye prompt con:
       - System prompt (desde archivo configurable).
       - Historial conversacional.
       - Contexto RAG (máximo 2048 tokens).
       - Pregunta del usuario.
    6. Envía a ProviderRouter.generate_stream().
    7. Almacena pregunta y respuesta en historial.
    8. Retorna stream de tokens + fuentes.
    """
```

#### 2.6.2 DocumentService

```python
class DocumentService:
    """
    Gestión del ciclo de vida de documentos.

    - upload: validar, guardar archivo, iniciar ingesta async.
    - delete: eliminar archivo + chunks + metadata.
    - list: listar documentos con estado (processing/ready/error).
    """
```

---

## 3. Componentes del Frontend

### 3.1 Estructura de Componentes

```
App.tsx
└── AppLayout.tsx
    ├── Header.tsx
    ├── Sidebar.tsx
    │   ├── ChatList (inline)
    │   └── DocumentList (inline)
    └── Main Content (via React Router)
        ├── HomePage.tsx
        ├── ChatPage.tsx
        │   ├── ChatContainer.tsx
        │   │   ├── ChatMessage.tsx (lista)
        │   │   └── ChatInput.tsx
        │   └── DocumentPanel.tsx
        ├── DocumentsPage.tsx
        │   ├── FileUpload.tsx
        │   └── DocumentList (inline)
        ├── SettingsPage.tsx
        │   └── ProviderSelector (inline)
        └── NotFoundPage.tsx
```

### 3.2 Estado Global (Zustand)

```typescript
// chatStore.ts
interface ChatStore {
  sessions: Record<string, Message[]>;
  activeSession: string | null;
  isStreaming: boolean;
  // Actions
  sendMessage: (message: string) => Promise<void>;
  addToken: (sessionId: string, token: string) => void;
  clearSession: (sessionId: string) => void;
}

// documentStore.ts
interface DocumentStore {
  documents: Document[];
  isUploading: boolean;
  // Actions
  fetchDocuments: () => Promise<void>;
  uploadDocument: (file: File) => Promise<void>;
  deleteDocument: (id: string) => Promise<void>;
}

// settingsStore.ts
interface SettingsStore {
  activeProvider: string;
  availableProviders: Provider[];
  // Actions
  fetchProviders: () => Promise<void>;
  switchProvider: (provider: string) => Promise<void>;
}
```

### 3.3 Servicios API

```typescript
// api.ts — Axios instance
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  timeout: 30000,
});

// Interceptor: logs, errores, refresh token stub
api.interceptors.response.use(
  (response) => response,
  (error) => {
    loguru.error("API Error", error);
    return Promise.reject(error);
  }
);

// chatService.ts
export const chatService = {
  sendMessage: (message: string, sessionId: string): Promise<EventSource> => {
    // POST /chat via fetch → SSE
  },
};

// documentService.ts
export const documentService = {
  upload: (file: File): Promise<Document> => { ... },
  list: (): Promise<Document[]> => { ... },
  delete: (id: string): Promise<void> => { ... },
};

// providerService.ts
export const providerService = {
  list: (): Promise<Provider[]> => { ... },
  switch: (provider: string): Promise<void> => { ... },
};
```

### 3.4 Manejo de SSE en Frontend

```typescript
// Hook: useChat.ts
export function useChat() {
  const { activeSession, addToken, setStreaming } = useChatStore();

  const sendMessage = async (message: string) => {
    const sessionId = activeSession;
    const response = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = JSON.parse(line.slice(6));
          if (data.done) {
            setStreaming(false);
          } else {
            addToken(sessionId, data.token);
          }
        }
      }
    }
  };

  return { sendMessage };
}
```

---

## 4. Integración n8n

### 4.1 Arquitectura

```
n8n ─── webhook ───► Backend API ───► Procesar request ───► Responder
       ◄─────────────── webhook response ─────────────────
```

### 4.2 Webhooks Expuestos

| Webhook | Método | Propósito |
|---------|--------|-----------|
| `/webhooks/n8n/chat` | POST | n8n envía preguntas al agente |
| `/webhooks/n8n/document` | POST | n8n gatilla ingesta de documentos |
| `/webhooks/n8n/event` | POST | n8n recibe eventos del sistema |

### 4.3 Ejemplo de Workflow n8n

```json
{
  "name": "Chat desde Slack",
  "nodes": [
    {
      "name": "Slack Trigger",
      "type": "n8n-nodes-base.slackTrigger",
      "parameters": {}
    },
    {
      "name": "HTTP Request",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://backend:8000/webhooks/n8n/chat",
        "method": "POST",
        "body": {
          "message": "={{ $json.text }}",
          "session_id": "={{ $json.user }}"
        }
      }
    },
    {
      "name": "Slack Response",
      "type": "n8n-nodes-base.slack",
      "parameters": {
        "channel": "={{ $json.channel }}",
        "text": "={{ $json.response }}"
      }
    }
  ]
}
```

---

## 5. Despliegue con Docker Compose

### 5.1 Estructura `docker-compose.yml`

```yaml
version: "3.9"

services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    volumes:
      - ./backend:/app
      - chroma_data:/app/chroma_data
      - uploads:/app/uploads
    depends_on:
      qdrant:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s

  frontend:
    build: ./frontend
    ports: ["5173:80"]
    depends_on: [backend]

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]

  n8n:
    image: n8nio/n8n:latest
    ports: ["5678:5678"]
    volumes:
      - n8n_data:/home/node/.n8n
    env_file: .env

volumes:
  chroma_data:
  qdrant_data:
  uploads:
  n8n_data:
```

### 5.2 Modo Desarrollo Local (sin Docker)

```bash
# Terminal 1: Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm install
npm run dev

# Terminal 3: ChromaDB (si no usas Qdrant)
# ChromaDB corre embebido en el proceso de Python
```

---

## 6. Prompt Engineering

### 6.1 System Prompt Default

```
Eres un asistente de IA experto en análisis de documentos.
Tu función es responder preguntas basándote ÚNICAMENTE en el contexto proporcionado.

REGLAS:
1. Siempre cita la fuente (nombre del documento) en tu respuesta.
2. Si no encuentras la información en el contexto, di: "No tengo información suficiente en los documentos cargados para responder esta pregunta."
3. No inventes información ni uses conocimiento externo.
4. Responde en el mismo idioma de la pregunta.
5. Sé conciso pero completo.
6. Si la pregunta es ambigua, pide aclaración antes de responder.
```

### 6.2 Estructura del Prompt Final

```
<system_prompt>
{system_prompt}
</system_prompt>

<conversation_history>
{historial de últimos N intercambios}
</conversation_history>

<context>
{chunks relevantes recuperados, cada uno con etiqueta source}
</context>

<user_question>
{pregunta actual}
</user_question>

<instructions>
Basándote en el contexto proporcionado, responde la pregunta del usuario.
Si usaste información del contexto, indica la fuente al final: [Fuente: nombre_documento]
</instructions>
```

---

## 7. Manejo de Errores

### 7.1 Estrategia General

```
Error ocurre
    │
    ├── Provider error → log + failover al siguiente provider
    │   ├── Rate limit → esperar y reintentar (1 vez), luego failover
    │   ├── Timeout → failover inmediato
    │   └── Auth error → failover + marcar como degraded
    │
    ├── RAG error → log + respuesta informativa al usuario
    │   ├── Document not found → 404
    │   └── Embedding error → reintentar con fallback
    │
    ├── Validation error → 422 con detalle del campo inválido
    │
    └── Internal error → 500 + log completo (sin exponer internals)
```

### 7.2 Códigos de Error API

```json
{
    "error": {
        "code": "PROVIDER_RATE_LIMITED",
        "message": "El proveedor Gemini ha excedido su cuota. Cambiando a Groq...",
        "details": {
            "provider": "google-gemini",
            "retry_after": 60
        }
    }
}
```

---

## 8. Testing

### 8.1 Backend

```
tests/
├── conftest.py              # Fixtures: app, client, mock providers, test docs
├── test_rag/
│   ├── test_loader.py       # PDF, CSV loading tests
│   ├── test_splitter.py     # Chunking tests
│   └── test_retriever.py    # Search tests
├── test_llm/
│   ├── test_providers.py    # Each provider with mocked HTTP
│   ├── test_router.py       # Router logic, failover, circuit breaker
│   └── test_fallback.py     # Retry, backoff, degradation
└── test_api/
    ├── test_chat.py         # Chat endpoint tests
    ├── test_documents.py    # Document CRUD tests
    ├── test_health.py       # Health check tests
    └── test_providers_api.py # Provider API tests
```

### 8.2 Frontend

```
src/
└── __tests__/
    ├── components/
    │   ├── ChatMessage.test.tsx
    │   ├── ChatInput.test.tsx
    │   └── FileUpload.test.tsx
    ├── hooks/
    │   ├── useChat.test.ts
    │   └── useDocuments.test.ts
    └── services/
        ├── chatService.test.ts
        └── documentService.test.ts
```

---

## 9. Configuración de CI/CD (GitHub Actions)

### Workflow: Tests

```yaml
name: CI
on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r backend/requirements-dev.txt
      - run: ruff check backend/
      - run: ruff format --check backend/
      - run: mypy --strict backend/
      - run: pytest backend/tests/ --cov=app --cov-report=term-missing

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "22" }
      - run: npm ci
        working-directory: frontend
      - run: npm run lint
        working-directory: frontend
      - run: npm run typecheck
        working-directory: frontend
      - run: npm test -- --coverage
        working-directory: frontend
```
