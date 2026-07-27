# AGENTS.md — Guía para el Asistente AI

## Identidad del Proyecto

**Challenge ONE AI FOR TECH — Alura Latam**
Agente inteligente con RAG, soporte multi-provider LLM, interfaz web y orquestación vía n8n.

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12+ / FastAPI / Uvicorn |
| Frontend | React 19 + TypeScript + Tailwind CSS v4 + Vite |
| Base de Datos | PostgreSQL 17 + pgvector |
| Vector Store | pgvector (cosine similarity) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) o API Gemini |
| LLM Providers | Google Gemini Free, Groq, DeepSeek, OpenAI-compatible |
| Auth | JWT (pyjwt) + API Key opcional |
| Observabilidad | Prometheus metrics + Loguru estructurado |
| Reverse Proxy | Caddy (HTTPS automático) |
| Orquestación | n8n (workflows visuales + webhooks) |
| Contenedores | Docker Compose |
| CI/CD | GitHub Actions |
| Documentación | Markdown + OpenAPI (FastAPI auto-docs) |

## Convenciones de Código

### Python (Backend)
- **Python 3.12+** — usar `str | None` en vez de `Optional[str]`
- **FastAPI** con inyección de dependencias (`Depends`)
- **Pydantic v2** para schemas de request/response
- **Async/await** en toda la capa de red, DB y RAG
- **SQLAlchemy 2.0 async** para PostgreSQL
- **Logging estructurado** con `loguru`
- **Tipado estricto** — `mypy --strict` en CI
- Formateador: `ruff format`
- Linter: `ruff check`

### TypeScript (Frontend)
- **TypeScript estricto** — `strict: true` en tsconfig
- **Componentes funcionales** con hooks, sin clases
- **Zustand** para estado global del chat y auth
- **React Query / TanStack Query** para llamadas API
- **Path aliases**: `@/components/*`, `@/pages/*`, `@/services/*`, `@/types/*`
- Formateador: `prettier`
- Linter: `oxlint`

### Estructura de Carpetas

```
/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app entry
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py          # POST /auth/login (JWT)
│   │   │   │   ├── chat.py          # POST /chat, streaming
│   │   │   │   ├── documents.py     # POST /documents/upload, DELETE
│   │   │   │   ├── health.py        # GET /health (real checks)
│   │   │   │   └── providers.py     # GET /providers, POST /providers/switch
│   │   │   └── middleware/
│   │   │       ├── __init__.py
│   │   │       ├── cors.py
│   │   │       ├── rate_limit.py
│   │   │       └── metrics.py       # Prometheus middleware
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # JWT + API key middleware
│   │   │   ├── config.py            # Pydantic Settings (30+ vars)
│   │   │   ├── database.py          # Async SQLAlchemy engine
│   │   │   ├── models.py            # ORM: DocumentRecord, ChunkRecord, ChatSessionRecord
│   │   │   ├── exceptions.py        # Error handling unificado
│   │   │   ├── logging.py           # JSON log config
│   │   │   ├── security.py          # PII filter, MIME validation, injection detection
│   │   │   └── dependencies.py      # Inyección de dependencias
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Abstract BaseProvider
│   │   │   ├── router.py            # ProviderRouter (fallback lógico)
│   │   │   ├── providers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── gemini.py
│   │   │   │   ├── groq.py
│   │   │   │   ├── deepseek.py
│   │   │   │   └── openai_compatible.py
│   │   │   └── fallback.py
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── ingestion/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── loader.py        # Carga PDF/CSV
│   │   │   │   ├── splitter.py      # Chunking semántico
│   │   │   │   └── processor.py     # Pipeline de ingesta
│   │   │   ├── retrieval/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── retriever.py     # Búsqueda vectorial pgvector
│   │   │   │   └── reranker.py
│   │   │   ├── embeddings/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py          # Abstract EmbeddingProvider
│   │   │   │   ├── local.py         # sentence-transformers
│   │   │   │   └── api.py           # Embeddings vía API (Gemini)
│   │   │   └── vector_store/
│   │   │       ├── __init__.py
│   │   │       ├── base.py          # Abstract VectorStore
│   │   │       ├── pgvector.py      # pgvector implementation (default)
│   │   │       ├── chroma.py        # ChromaDB (legacy)
│   │   │       └── qdrant.py        # Qdrant production option
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   └── chat_history.py      # Memoria conversacional en PostgreSQL
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── chat_service.py      # Orquestación del chat
│   │       └── document_service.py  # Gestión de documentos (PostgreSQL)
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_rag/
│   │   ├── test_llm/
│   │   └── test_api/
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   ├── FileUpload.tsx
│   │   │   │   ├── ProtectedRoute.tsx  # Auth guard
│   │   │   │   ├── Spinner.tsx
│   │   │   │   └── Toast.tsx
│   │   │   ├── layout/
│   │   │   │   ├── AppLayout.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Header.tsx
│   │   │   │   └── Footer.tsx
│   │   │   └── chat/
│   │   │       ├── ChatContainer.tsx
│   │   │       ├── ChatMessage.tsx
│   │   │       ├── ChatInput.tsx
│   │   │       └── DocumentPanel.tsx
│   │   ├── pages/
│   │   │   ├── HomePage.tsx
│   │   │   ├── ChatPage.tsx
│   │   │   ├── DocumentsPage.tsx
│   │   │   ├── LoginPage.tsx        # JWT login
│   │   │   ├── SettingsPage.tsx
│   │   │   └── NotFoundPage.tsx
│   │   ├── hooks/
│   │   │   ├── useChat.ts
│   │   │   ├── useDocuments.ts
│   │   │   └── useProviders.ts
│   │   ├── services/
│   │   │   ├── api.ts               # Axios + JWT interceptor
│   │   │   ├── chatService.ts
│   │   │   ├── documentService.ts
│   │   │   └── providerService.ts
│   │   ├── store/
│   │   │   ├── authStore.ts         # Zustand auth state
│   │   │   ├── chatStore.ts         # Zustand chat state
│   │   │   ├── documentStore.ts
│   │   │   └── settingsStore.ts
│   │   └── types/
│   │       ├── auth.ts
│   │       ├── chat.ts
│   │       ├── document.ts
│   │       └── provider.ts
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   ├── Dockerfile
│   └── .env.example
├── n8n/
│   ├── docker-compose.yml
│   └── workflows/
│       └── example_webhook.json
├── .github/workflows/
│   └── ci.yml                      # CI/CD pipeline
├── Caddyfile                        # Reverse proxy + HTTPS
├── docker-compose.yml               # Orquestación completa
├── .env.example
├── AGENTS.md
├── requirements.md
├── design.md
├── tasks.md
└── README.md
```

## Reglas de Implementación

1. **No acoplar providers**: Cada LLM provider implementa `BaseProvider` con interfaz unificada. El `ProviderRouter` decide cuál usar.
2. **Fallback obligatorio**: Si un provider falla (rate limit, timeout), el sistema debe rotar al siguiente automáticamente.
3. **Embeddings locales por defecto**: Usar `sentence-transformers` para evitar depender de APIs externas en el pipeline de ingesta. Embeddings API como respaldo.
4. **CORS configurado**: El backend debe permitir orígenes del frontend en desarrollo (`http://localhost:5173`) y producción (`http://localhost:3000`).
5. **Streaming**: El chat debe usar Server-Sent Events (SSE) para streaming de respuestas.
6. **Chunking semántico**: Los documentos se dividen en chunks con overlap usando `RecursiveCharacterTextSplitter`.
7. **Prompt engineering**: El system prompt debe ser configurable vía variable de entorno.
8. **n8n como orquestador complementario**: n8n recibe webhooks del backend para workflows externos (no es dependencia crítica).
9. **Persistencia PostgreSQL**: Toda la metadata se persiste en PostgreSQL. No usar estado en memoria.
10. **Async DB**: Toda operación de base de datos debe ser async con SQLAlchemy 2.0 + asyncpg.

## Reglas de Seguridad

1. **Auth dual**: Si `API_KEY` está configurada, todos los endpoints (excepto `/health` y `/auth/login`) requieren JWT Bearer token o header `X-API-Key`.
2. **JWT**: Login vía `POST /auth/login` con `ADMIN_USERNAME`/`ADMIN_PASSWORD`. Token configurable via `JWT_EXPIRE_MINUTES`.
3. **Límite de archivos**: Upload máximo 50MB controlado por `MAX_UPLOAD_SIZE_MB`. Validación de magic bytes para PDF (`%PDF` header).
4. **Contexto delimitado**: El contexto RAG se envía al LLM envuelto en `<contexto_documentos>...</contexto_documentos>`.
5. **Filtro PII**: Las respuestas del LLM se filtran con regex antes de enviarlas al cliente (emails, teléfonos, DNIs, credit cards, passwords).
6. **Session IDs**: Si el cliente no envía `session_id`, el servidor genera uno con `secrets.token_hex(16)`.
7. **Mensajes de error sanitizados**: Los errores de providers LLM nunca exponen detalles de la API.
8. **Rate limiting**: 100 requests/min por IP (respeta `X-Forwarded-For`).
9. **Security headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `HSTS`, `Cross-Origin-Resource-Policy: same-origin`.
10. **Path traversal**: `DocumentService._safe_path()` resuelve y valida que el path esté dentro de `UPLOAD_DIR`.
11. **Límite de extracción**: Máximo 5M caracteres extraídos por documento (`MAX_EXTRACTED_CHARS`). Máximo 5000 chunks (`MAX_CHUNKS_PER_DOCUMENT`).
12. **Timeouts**: Llamadas a LLM providers con `asyncio.timeout()` controlado por `LLM_TIMEOUT_SECONDS`.

## Flujo de Chat

```
Usuario → Frontend (login JWT) → HTTP SSE (Authorization: Bearer) → Backend (FastAPI)
  → ProviderRouter con timeout y fallback
  → Retriever (pgvector cosine similarity)
  → Construye prompt con contexto + historial (PostgreSQL)
  → LLM genera respuesta (streaming con timeout)
  → Backend filtra PII, envía tokens SSE → Frontend renderiza
```

## Prioridad de Providers (por defecto)

1. Google Gemini (gratuito, 60 req/min)
2. Groq (gratuito, 30 req/min, modelos abiertos)
3. DeepSeek (costo bajo, buen rendimiento)
4. OpenAI-compatible (OpenRouter, Together, etc.)

El `ProviderRouter` chequea salud, cuota y timeout antes de cada request. Rotación automática con circuit breaker (3 fallos → 60s degraded).

## Variables de Entorno Críticas

```env
# LLM Providers
GEMINI_API_KEY=
GROQ_API_KEY=
DEEPSEEK_API_KEY=
OPENAI_COMPATIBLE_API_KEY=
OPENAI_COMPATIBLE_BASE_URL=

# Vector Store
VECTOR_STORE_TYPE=pgvector|chroma|qdrant
QDRANT_URL=
QDRANT_API_KEY=

# Embeddings
EMBEDDING_PROVIDER=local|api
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Security
API_KEY=                              # Protege endpoints (vacío = sin auth)
JWT_SECRET=change-me-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
MAX_UPLOAD_SIZE_MB=50
MAX_CHUNKS_PER_DOCUMENT=5000
MAX_EXTRACTED_CHARS=5000000
RETRIEVAL_SCORE_THRESHOLD=0.45

# Database
DATABASE_URL=postgresql+asyncpg://agent:agent@localhost:5432/agent

# Backend
LOG_LEVEL=DEBUG|INFO|WARNING
MAX_TOKENS=4096
TEMPERATURE=0.7
SYSTEM_PROMPT_PATH=./prompts/system.txt
LLM_TIMEOUT_SECONDS=60
LLM_RETRY_MAX_ATTEMPTS=3
LLM_RETRY_BASE_DELAY=1.0

# CORS
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Frontend
VITE_API_BASE_URL=http://localhost:8000
```

## Testing

- Backend: `pytest` con `pytest-asyncio`, cobertura mínima 80%
- Frontend: `vitest` + `@testing-library/react`
- RAG: tests de integración con PostgreSQL + pgvector
- Fallback: tests unitarios simulando errores de providers
- CI/CD: GitHub Actions corre lint + test + build en cada push

## Commits Convencionales

```
feat: agregar provider DeepSeek con fallback
fix: manejar timeout en conexión PostgreSQL
docs: actualizar README con ejemplos de preguntas
refactor: migrar de ChromaDB a pgvector
test: agregar tests para auth JWT
chore: actualizar dependencias FastAPI
```
