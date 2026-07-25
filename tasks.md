# Tasks.md — Plan de Implementación

## Challenge ONE AI FOR TECH — Alura Latam

---

## Convenciones

- **Formato**: `{Categoría}-{Número}: {Verbo} {acción}`
- **Estimación**: S (≤2h), M (2-4h), L (4-8h), XL (8-16h)
- **Dependencia**: Tarea que debe completarse antes
- **Prioridad**: 🔴 Crítica | 🟡 Alta | 🟢 Media | 🔵 Baja
- **Estado**: ⬜ Pendiente | 🔄 En progreso | ✅ Completada

---

## Fase 0: Inicialización del Proyecto ⬜

| ID | Tarea | Prioridad | Estimación | Dependencia |
|----|-------|-----------|------------|-------------|
| T-000 | Crear estructura de directorios del proyecto | 🔴 | S | — |
| T-001 | Configurar repositorio Git + .gitignore | 🔴 | S | T-000 |
| T-002 | Crear `.env.example` con todas las variables | 🔴 | S | T-000 |
| T-003 | Crear `docker-compose.yml` base (backend + frontend + qdrant + n8n) | 🔴 | M | T-000 |
| T-004 | Crear `README.md` con descripción general + instrucciones + ejemplos | 🔴 | M | T-013 |
| T-005 | Configurar CI/CD (GitHub Actions: lint + test + typecheck) | 🟡 | M | T-000 |

---

## Fase 1: Backend — Core y Configuración ⬜

| ID | Tarea | Prioridad | Estimación | Dependencia |
|----|-------|-----------|------------|-------------|
| T-100 | Crear estructura de backend (`app/`, `api/`, `core/`, etc.) | 🔴 | S | T-000 |
| T-101 | Implementar `app/core/config.py` — Pydantic Settings con carga `.env` | 🔴 | S | T-100 |
| T-102 | Implementar `app/core/exceptions.py` — jerarquía de excepciones | 🔴 | M | T-100 |
| T-103 | Implementar `app/core/dependencies.py` — inyección de dependencias | 🔴 | M | T-101, T-102 |
| T-104 | Implementar `app/main.py` — FastAPI app factory, lifespan, routers | 🔴 | M | T-100 |
| T-105 | Implementar `app/api/routes/health.py` — GET /health | 🔴 | S | T-104 |
| T-106 | Implementar CORS middleware (`app/api/middleware/cors.py`) | 🔴 | S | T-104 |
| T-107 | Implementar rate limiter middleware (`app/api/middleware/rate_limit.py`) | 🟡 | M | T-104 |
| T-108 | Crear `requirements.txt` y `requirements-dev.txt` con dependencias | 🔴 | S | T-100 |
| T-109 | Crear `Dockerfile` para backend | 🔴 | S | T-104 |

---

## Fase 2: Backend — Embeddings ⬜

| ID | Tarea | Prioridad | Estimación | Dependencia |
|----|-------|-----------|------------|-------------|
| T-200 | Implementar `app/rag/embeddings/base.py` — Abstract EmbeddingProvider | 🔴 | S | T-100 |
| T-201 | Implementar `app/rag/embeddings/local.py` — sentence-transformers wrapper | 🔴 | M | T-200 |
| T-202 | Implementar `app/rag/embeddings/api.py` — Gemini Embeddings API | 🟡 | M | T-200 |

---

## Fase 3: Backend — Vector Store ⬜

| ID | Tarea | Prioridad | Estimación | Dependencia |
|----|-------|-----------|------------|-------------|
| T-300 | Implementar `app/rag/vector_store/base.py` — Abstract VectorStore | 🔴 | S | T-100 |
| T-301 | Implementar `app/rag/vector_store/chroma.py` — ChromaDB persistente | 🔴 | M | T-300 |
| T-302 | Implementar `app/rag/vector_store/qdrant.py` — Qdrant client | 🟢 | M | T-300 |

---

## Fase 4: Backend — Pipeline de Ingesta ⬜

| ID | Tarea | Prioridad | Estimación | Dependencia |
|----|-------|-----------|------------|-------------|
| T-400 | Implementar `app/rag/ingestion/loader.py` — PDF (PyMuPDF) + CSV | 🔴 | M | T-100 |
| T-401 | Implementar `app/rag/ingestion/splitter.py` — SemanticChunker | 🔴 | M | T-100 |
| T-402 | Implementar `app/rag/ingestion/processor.py` — IngestionProcessor orquestador | 🔴 | M | T-400, T-401, T-201, T-301 |
| T-403 | Implementar `app/rag/retrieval/retriever.py` — Retriever con búsqueda semántica | 🔴 | M | T-402 |
| T-404 | Implementar `app/rag/retrieval/reranker.py` — CrossEncoderReranker | 🟢 | L | T-403 |
| T-405 | Implementar `app/services/document_service.py` — upload, list, delete | 🔴 | M | T-402 |

---

## Fase 5: Backend — LLM Multi-Provider ⬜

| ID | Tarea | Prioridad | Estimación | Dependencia |
|----|-------|-----------|------------|-------------|
| T-500 | Implementar `app/llm/base.py` — Abstract BaseProvider | 🔴 | M | T-100 |
| T-501 | Implementar `app/llm/providers/gemini.py` — GeminiProvider | 🔴 | M | T-500 |
| T-502 | Implementar `app/llm/providers/groq.py` — GroqProvider | 🔴 | M | T-500 |
| T-503 | Implementar `app/llm/providers/deepseek.py` — DeepSeekProvider | 🟡 | M | T-500 |
| T-504 | Implementar `app/llm/providers/openai_compatible.py` — OpenAICompatibleProvider | 🟡 | M | T-500 |
| T-505 | Implementar `app/llm/router.py` — ProviderRouter con selección y failover | 🔴 | L | T-501..T-504 |
| T-506 | Implementar `app/llm/fallback.py` — Circuit breaker + exponential backoff | 🔴 | M | T-505 |
| T-507 | Implementar `app/memory/chat_history.py` — ChatHistoryManager (SQLite) | 🔴 | M | T-100 |

---

## Fase 6: Backend — Servicios y APIs ⬜

| ID | Tarea | Prioridad | Estimación | Dependencia |
|----|-------|-----------|------------|-------------|
| T-600 | Implementar `app/services/chat_service.py` — ChatService (orquestación chat) | 🔴 | L | T-403, T-505, T-507 |
| T-601 | Implementar `app/api/routes/chat.py` — POST /chat con SSE streaming | 🔴 | M | T-600 |
| T-602 | Implementar `app/api/routes/documents.py` — CRUD documentos | 🔴 | M | T-405 |
| T-603 | Implementar `app/api/routes/providers.py` — GET/POST providers | 🟡 | M | T-505 |
| T-604 | Implementar webhooks n8n (`app/api/routes/webhooks.py`) | 🔵 | M | T-600 |

---

## Fase 7: Frontend — Configuración Inicial ⬜

| ID | Tarea | Prioridad | Estimación | Dependencia |
|----|-------|-----------|------------|-------------|
| T-700 | Inicializar proyecto Vite + React 19 + TypeScript | 🔴 | S | T-000 |
| T-701 | Configurar Tailwind CSS v4 + PostCSS | 🔴 | S | T-700 |
| T-702 | Configurar path aliases (`@/`) en tsconfig + vite.config | 🔴 | S | T-700 |
| T-703 | Configurar ESLint + Prettier para TypeScript/React | 🟡 | S | T-700 |
| T-704 | Instalar dependencias: zustand, axios, react-router-dom, tanstack-query | 🔴 | S | T-700 |
| T-705 | Crear `Dockerfile` para frontend (nginx + build estático) | 🟡 | S | T-700 |
| T-706 | Implementar `src/services/api.ts` — Axios instance + interceptors | 🔴 | S | T-704 |
| T-707 | Implementar tipos TypeScript (`src/types/chat.ts`, `document.ts`, `provider.ts`) | 🔴 | M | T-700 |

---

## Fase 8: Frontend — Componentes Comunes y Layout ⬜

| ID | Tarea | Prioridad | Estimación | Dependencia |
|----|-------|-----------|------------|-------------|
| T-800 | Implementar `Button.tsx` — variantes, loading state, disabled | 🔴 | S | T-700 |
| T-801 | Implementar `Input.tsx` — input con icono, error state | 🔴 | S | T-700 |
| T-802 | Implementar `Modal.tsx` — modal accesible con overlay | 🟡 | M | T-700 |
| T-803 | Implementar `FileUpload.tsx` — drag-and-drop + validación | 🔴 | M | T-700 |
| T-804 | Implementar `Spinner.tsx` — loading spinner animado | 🔴 | S | T-700 |
| T-805 | Implementar `Toast.tsx` — notificaciones toast | 🟡 | M | T-700 |
| T-806 | Implementar `AppLayout.tsx` — layout principal con header + sidebar + main | 🔴 | M | T-700 |
| T-807 | Implementar `Header.tsx` — logo, título, nav | 🔴 | S | T-806 |
| T-808 | Implementar `Sidebar.tsx` — navegación, lista sesiones, docs | 🔴 | M | T-806 |
| T-809 | Implementar `Footer.tsx` — información del sistema | 🟢 | S | T-806 |

---

## Fase 9: Frontend — Módulo de Chat ⬜

| ID | Tarea | Prioridad | Estimación | Dependencia |
|----|-------|-----------|------------|-------------|
| T-900 | Implementar `ChatContainer.tsx` — contenedor del chat con scroll automático | 🔴 | M | T-700 |
| T-901 | Implementar `ChatMessage.tsx` — burbuja de mensaje (user/agent) + fuentes | 🔴 | M | T-700 |
| T-902 | Implementar `ChatInput.tsx` — input + botón enviar (soporta Enter) | 🔴 | S | T-700 |
| T-903 | Implementar `DocumentPanel.tsx` — panel lateral con documentos cargados | 🟡 | M | T-700 |
| T-904 | Implementar `src/hooks/useChat.ts` — hook de chat con SSE y buffer | 🔴 | M | T-706, T-707 |
| T-905 | Implementar `src/store/chatStore.ts` — Zustand store del chat | 🔴 | M | T-704 |
| T-906 | Implementar `src/services/chatService.ts` — llamadas API de chat | 🔴 | S | T-706 |

---

## Fase 10: Frontend — Páginas ⬜

| ID | Tarea | Prioridad | Estimación | Dependencia |
|----|-------|-----------|------------|-------------|
| T-1000 | Implementar `HomePage.tsx` — landing page con descripción del proyecto | 🟡 | M | T-806 |
| T-1001 | Implementar `ChatPage.tsx` — página principal de chat | 🔴 | M | T-900..T-902, T-806 |
| T-1002 | Implementar `DocumentsPage.tsx` — gestión de documentos | 🔴 | M | T-803, T-806 |
| T-1003 | Implementar `SettingsPage.tsx` — configuración de providers | 🟡 | M | T-806 |
| T-1004 | Implementar `NotFoundPage.tsx` — 404 personalizada | 🟢 | S | T-806 |
| T-1005 | Implementar `App.tsx` — React Router con todas las rutas | 🔴 | S | T-1000..T-1004 |
| T-1006 | Implementar `main.tsx` — entry point con providers | 🔴 | S | T-1005 |
| T-1007 | Implementar hooks adicionales: `useDocuments.ts`, `useProviders.ts` | 🟡 | M | T-706 |
| T-1008 | Implementar stores adicionales: `documentStore.ts`, `settingsStore.ts` | 🟡 | M | T-704 |
| T-1009 | Implementar services adicionales: `documentService.ts`, `providerService.ts` | 🟡 | S | T-706 |

---

## Fase 11: Integración n8n ⬜

| ID | Tarea | Prioridad | Estimación | Dependencia |
|----|-------|-----------|------------|-------------|
| T-1100 | Configurar n8n en `docker-compose.yml` con volúmenes persistentes | 🔵 | S | T-003 |
| T-1101 | Implementar webhooks n8n en backend (si no se hizo en T-604) | 🔵 | M | T-104 |
| T-1102 | Crear workflow n8n de ejemplo (Slack ↔ Agente) | 🔵 | M | T-1100 |
| T-1103 | Documentar integración n8n en README | 🔵 | S | T-1102 |

---

## Fase 12: Testing ⬜

| ID | Tarea | Prioridad | Estimación | Dependencia |
|----|-------|-----------|------------|-------------|
| T-1200 | Crear `conftest.py` con fixtures globales (app, client, mock providers) | 🔴 | M | T-104 |
| T-1201 | Implementar tests de embeddings (unitarios, local + api) | 🟡 | M | T-200, T-201 |
| T-1202 | Implementar tests de vector store (ChromaDB) | 🟡 | M | T-301 |
| T-1203 | Implementar tests de ingesta (loader, splitter, processor) | 🟡 | M | T-400..T-402 |
| T-1204 | Implementar tests de retrieval (retriever, reranker) | 🟡 | M | T-403, T-404 |
| T-1205 | Implementar tests de providers (cada provider con HTTP mocked) | 🔴 | M | T-501..T-504 |
| T-1206 | Implementar tests de router (fallback, circuit breaker, prioridad) | 🔴 | M | T-505 |
| T-1207 | Implementar tests de API endpoints (chat, documents, health, providers) | 🔴 | L | T-601..T-603 |
| T-1208 | Implementar tests de frontend (componentes + hooks) | 🟡 | M | T-900..T-904 |

---

## Fase 13: Pulido y Documentación ⬜

| ID | Tarea | Prioridad | Estimación | Dependencia |
|----|-------|-----------|------------|-------------|
| T-1300 | Verificar cobertura de tests >= 80% | 🔴 | S | Fase 12 |
| T-1301 | Ejecutar `ruff check` y `ruff format` en todo el backend | 🔴 | S | Fase 6 |
| T-1302 | Ejecutar ESLint + Prettier en todo el frontend | 🔴 | S | Fase 10 |
| T-1303 | Probar flujo completo con `docker compose up` | 🔴 | M | Fase 6, Fase 10 |
| T-1304 | Probar failover de providers (deshabilitar API key de Gemini) | 🔴 | S | T-1303 |
| T-1305 | Completar README.md con ejemplos de preguntas y respuestas | 🔴 | M | T-004 |
| T-1306 | Verificar que `.env.example` esté completo y sincronizado | 🔴 | S | T-002 |
| T-1307 | Push a GitHub + verificar que CI pase | 🔴 | S | T-005 |

---

## Dependencias Entre Fases

```
Fase 0 (Inicialización)
    │
    ├──► Fase 1 (Backend Core)
    │       │
    │       ├──► Fase 2 (Embeddings) ──► Fase 3 (Vector Store) ──► Fase 4 (Ingesta)
    │       │                                                           │
    │       └──► Fase 5 (LLM Multi-Provider) ────► Fase 6 (Servicios + APIs)
    │                                                     │
    └──► Fase 7 (Frontend Setup) ──► Fase 8 (Componentes) ──► Fase 9 (Chat)
                                                                  │
                                            ◄──────────────────────┘
                                            │
                                      Fase 10 (Páginas)
                                            │
                                      Fase 12 (Testing)
                                            │
                                      Fase 13 (Pulido)
```

---

## Resumen de Esfuerzo

| Fase | Tareas | Estimación Total |
|------|--------|------------------|
| Fase 0: Inicialización | 6 | ~8h |
| Fase 1: Backend Core | 10 | ~10h |
| Fase 2: Embeddings | 3 | ~5h |
| Fase 3: Vector Store | 3 | ~5h |
| Fase 4: Ingesta | 6 | ~20h |
| Fase 5: LLM Multi-Provider | 8 | ~24h |
| Fase 6: Servicios y APIs | 5 | ~16h |
| Fase 7: Frontend Setup | 8 | ~6h |
| Fase 8: Componentes Comunes | 10 | ~12h |
| Fase 9: Módulo Chat | 7 | ~14h |
| Fase 10: Páginas | 10 | ~16h |
| Fase 11: n8n | 4 | ~6h |
| Fase 12: Testing | 9 | ~24h |
| Fase 13: Pulido | 8 | ~12h |
| **Total** | **97** | **~178h** |

---

## Orden Sugerido de Implementación (Top 20 Tareas Críticas)

| Orden | ID | Tarea | ¿Por qué primero? |
|-------|----|-------|-------------------|
| 1 | T-000 | Estructura de directorios | Base de todo |
| 2 | T-001 | Git + .gitignore | Control de versiones desde el inicio |
| 3 | T-002 | .env.example | Define el contrato de configuración |
| 4 | T-108 | requirements.txt | Dependencias del backend |
| 5 | T-104 | main.py (FastAPI app) | Entry point del backend |
| 6 | T-101 | config.py (Pydantic Settings) | Configuración centralizada |
| 7 | T-105 | health.py endpoint | Verificar que el backend funciona |
| 8 | T-106 | CORS middleware | Conexión frontend-backend |
| 9 | T-200..T-201 | Embeddings locales | Pipeline RAG sin API keys |
| 10 | T-300..T-301 | ChromaDB vector store | Almacenamiento de vectores local |
| 11 | T-400..T-402 | Pipeline de ingesta | Leer PDFs y guardar vectores |
| 12 | T-403 | Retriever | Búsqueda semántica básica |
| 13 | T-500 | BaseProvider (abstracto) | Define el contrato LLM |
| 14 | T-501 | Gemini provider | Provider gratuito principal |
| 15 | T-505 | ProviderRouter | Failover automático |
| 16 | T-502 | Groq provider | Segundo provider gratuito |
| 17 | T-507 | ChatHistoryManager | Memoria conversacional |
| 18 | T-600..T-601 | ChatService + API | ¡El chat funciona! |
| 19 | T-700 | Frontend setup | Empieza la interfaz |
| 20 | T-1001 | ChatPage + T-1005 App.tsx | ¡MVP completo! |
