# AGENTS.md — Guía para el Asistente AI

## Identidad del Proyecto

**Challenge ONE AI FOR TECH — Alura Latam**
Agente inteligente con RAG, soporte multi-provider LLM, interfaz web y orquestación vía n8n.

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12+ / FastAPI / Uvicorn |
| Frontend | React 19 + TypeScript + Tailwind CSS v4 + Vite |
| Base de Datos Vectorial | ChromaDB (local/desarrollo) / Qdrant (producción) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) o API Gemini |
| LLM Providers | Google Gemini Free, Groq, DeepSeek, OpenAI-compatible |
| Orquestación | n8n (workflows visuales + webhooks) |
| Contenedores | Docker Compose |
| Documentación | Markdown + OpenAPI (FastAPI auto-docs) |

## Convenciones de Código

### Python (Backend)
- **Python 3.12+** — usar `str | None` en vez de `Optional[str]`
- **FastAPI** con inyección de dependencias (`Depends`)
- **Pydantic v2** para schemas de request/response
- **Async/await** en toda la capa de red y RAG
- **Logging estructurado** con `loguru`
- **Tipado estricto** — `mypy --strict` en CI
- Formateador: `ruff format`
- Linter: `ruff check`

### TypeScript (Frontend)
- **TypeScript estricto** — `strict: true` en tsconfig
- **Componentes funcionales** con hooks, sin clases
- **Zustand** para estado global del chat
- **React Query / TanStack Query** para llamadas API
- **Path aliases**: `@/components/*`, `@/pages/*`, `@/services/*`, `@/types/*`
- Formateador: `prettier`
- Linter: `eslint` con config TypeScript

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
│   │   │   │   ├── chat.py          # POST /chat, streaming
│   │   │   │   ├── documents.py     # POST /documents/upload, DELETE
│   │   │   │   ├── health.py        # GET /health
│   │   │   │   └── providers.py     # GET /providers, POST /providers/switch
│   │   │   └── middleware/
│   │   │       ├── __init__.py
│   │   │       ├── cors.py
│   │   │       └── rate_limit.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py            # Pydantic Settings
│   │   │   ├── exceptions.py        # Error handling unificado
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
│   │   │   │   └── openai_compatible.py  # OpenAI API compat layer
│   │   │   └── fallback.py          # Lógica de reintento y failover
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── ingestion/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── loader.py        # Carga PDF/CSV
│   │   │   │   ├── splitter.py      # Chunking semántico
│   │   │   │   └── processor.py     # Pipeline de ingesta
│   │   │   ├── retrieval/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── retriever.py     # Búsqueda vectorial
│   │   │   │   └── reranker.py      # Re-ranking opcional
│   │   │   ├── embeddings/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py          # Abstract EmbeddingProvider
│   │   │   │   ├── local.py         # sentence-transformers
│   │   │   │   └── api.py           # Embeddings vía API (Gemini)
│   │   │   └── vector_store/
│   │   │       ├── __init__.py
│   │   │       ├── base.py          # Abstract VectorStore
│   │   │       ├── chroma.py        # ChromaDB implementation
│   │   │       └── qdrant.py        # Qdrant implementation
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   └── chat_history.py      # Memoria conversacional
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── chat_service.py      # Orquestación del chat
│   │       └── document_service.py  # Gestión de documentos
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
│   │   │   ├── SettingsPage.tsx
│   │   │   └── NotFoundPage.tsx
│   │   ├── hooks/
│   │   │   ├── useChat.ts
│   │   │   ├── useDocuments.ts
│   │   │   └── useProviders.ts
│   │   ├── services/
│   │   │   ├── api.ts               # Axios instance + interceptors
│   │   │   ├── chatService.ts
│   │   │   ├── documentService.ts
│   │   │   └── providerService.ts
│   │   ├── store/
│   │   │   ├── chatStore.ts          # Zustand
│   │   │   ├── documentStore.ts
│   │   │   └── settingsStore.ts
│   │   └── types/
│   │       ├── chat.ts
│   │       ├── document.ts
│   │       └── provider.ts
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── package.json
│   ├── Dockerfile
│   └── .env.example
├── n8n/
│   ├── docker-compose.yml
│   └── workflows/
│       └── example_webhook.json
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
3. **Embeddings locales por defecto**: Usar `sentence-transformers` para evitar depender de APIs gratuitas en el pipeline de ingesta. Embeddings API como respaldo.
4. **CORS configurado**: El backend debe permitir origen del frontend en desarrollo (`http://localhost:5173`).
5. **Streaming**: El chat debe usar Server-Sent Events (SSE) para streaming de respuestas.
6. **Chunking semántico**: Los documentos se dividen en chunks con overlap usando `RecursiveCharacterTextSplitter` de LangChain o similar.
7. **Prompt engineering**: El system prompt debe ser configurable vía variable de entorno.
8. **n8n como orquestador complementario**: n8n recibe webhooks del backend para workflows externos (no es dependencia crítica).

## Flujo de Chat (Resumen)

```
Usuario → Frontend (React) → HTTP SSE → Backend (FastAPI)
  → ProviderRouter (elige LLM según prioridad y disponibilidad)
  → Retriever (busca en vector store)
  → Construye prompt con contexto + historial
  → LLM genera respuesta (streaming)
  → Backend envía tokens SSE → Frontend renderiza
```

## Prioridad de Providers (por defecto)

1. Google Gemini (gratuito, 60 req/min)
2. Groq (gratuito, 30 req/min, modelos abiertos)
3. DeepSeek (costo bajo, buen rendimiento)
4. OpenAI-compatible (OpenRouter, Together, etc.)

El `ProviderRouter` chequea salud y cuota antes de cada request.

## Variables de Entorno Críticas

```env
# LLM Providers
GEMINI_API_KEY=
GROQ_API_KEY=
DEEPSEEK_API_KEY=
OPENAI_COMPATIBLE_API_KEY=
OPENAI_COMPATIBLE_BASE_URL=

# Vector Store
VECTOR_STORE_TYPE=chroma|qdrant
QDRANT_URL=
QDRANT_API_KEY=

# Embeddings
EMBEDDING_PROVIDER=local|api
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Backend
LOG_LEVEL=DEBUG|INFO|WARNING
MAX_TOKENS=4096
TEMPERATURE=0.7
SYSTEM_PROMPT_PATH=./prompts/system.txt

# Frontend
VITE_API_BASE_URL=http://localhost:8000
```

## Testing

- Backend: `pytest` con `pytest-asyncio`, cobertura mínima 80%
- Frontend: `vitest` + `@testing-library/react`
- RAG: tests de integración con documentos de prueba
- Fallback: tests unitarios simulando errores de providers

## Commits Convencionales

```
feat: agregar provider DeepSeek con fallback
fix: manejar timeout en conexión ChromaDB
docs: actualizar README con ejemplos de preguntas
refactor: extraer lógica de chunking a splitter.py
test: agregar tests para ProviderRouter
chore: actualizar dependencias FastAPI
```
