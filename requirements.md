# Requirements.md — Especificación de Requisitos

## Challenge ONE AI FOR TECH — Alura Latam

---

## 1. Visión General del Producto

Sistema agente inteligente con capacidad de **Retrieval-Augmented Generation (RAG)** que permite a usuarios cargar documentos (PDF/CSV) y realizar preguntas en lenguaje natural sobre su contenido. El sistema soporta **múltiples proveedores LLM** con failover automático, **memoria conversacional**, y una **interfaz web moderna**. Adicionalmente, se integra con **n8n** para orquestación de workflows externos.

### 1.1 Objetivos del Negocio

- Democratizar el acceso a IA generativa combinada con conocimiento propio (documentos).
- Proveer una solución **100% funcional en tier gratuita** (Gemini, Groq) con escalabilidad a providers de pago.
- Entregar una arquitectura lista para producción con Docker.
- Demostrar competencias en RAG, multi-provider LLM, frontend moderno y orquestación.

---

## 2. Requisitos Funcionales

### Módulo RF-01: Ingesta de Documentos

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-01.1 | El sistema debe aceptar archivos **PDF** y **CSV** como fuente de conocimiento | Alta |
| RF-01.2 | El sistema debe extraer texto completo de archivos PDF (incluyendo PDFs escaneados vía OCR básico) | Alta |
| RF-01.3 | El sistema debe parsear archivos CSV respetando delimitadores y codificación UTF-8 | Alta |
| RF-01.4 | El sistema debe dividir el texto extraído en **chunks semánticos** con tamaño configurable (default: 512 tokens) y overlap (default: 64 tokens) | Alta |
| RF-01.5 | El sistema debe generar **embeddings** para cada chunk y almacenarlos en una base de datos vectorial | Alta |
| RF-01.6 | El sistema debe permitir eliminar documentos y sus chunks asociados | Media |
| RF-01.7 | El sistema debe mostrar el progreso de ingesta en tiempo real | Media |

### Módulo RF-02: Consulta y Generación de Respuestas

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-02.1 | El usuario debe poder hacer preguntas en **lenguaje natural** sobre los documentos cargados | Alta |
| RF-02.2 | El sistema debe realizar **búsqueda semántica** en la base vectorial para recuperar los chunks más relevantes (top-k configurable, default: 5) | Alta |
| RF-02.3 | El sistema debe construir un **prompt enriquecido** con el contexto recuperado + historial de conversación | Alta |
| RF-02.4 | El sistema debe generar respuestas en **streaming** (Server-Sent Events) | Alta |
| RF-02.5 | El sistema debe citar las fuentes (nombre del documento + fragmento) en cada respuesta | Alta |
| RF-02.6 | El sistema debe mantener **memoria conversacional** por sesión (últimos N intercambios, default: 10) | Alta |

### Módulo RF-03: Multi-Provider LLM

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-03.1 | El sistema debe soportar **Google Gemini** (modelo gratuito: gemini-2.0-flash) | Alta |
| RF-03.2 | El sistema debe soportar **Groq** (modelo: llama-3.3-70b-versatile) | Alta |
| RF-03.3 | El sistema debe soportar **DeepSeek** (modelo: deepseek-chat) | Alta |
| RF-03.4 | El sistema debe soportar providers **OpenAI-compatible** (OpenRouter, Together, etc.) | Alta |
| RF-03.5 | El sistema debe implementar **failover automático**: si un provider falla (rate limit, timeout, 5xx), rotar al siguiente en orden de prioridad | Alta |
| RF-03.6 | El sistema debe verificar **salud y cuota** del provider antes de cada request | Alta |
| RF-03.7 | El usuario debe poder **cambiar el provider activo** manualmente desde la UI | Media |
| RF-03.8 | El sistema debe exponer el **estado de cada provider** (disponible/error/cuota) vía API | Media |

### Módulo RF-04: Interfaz de Usuario

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-04.1 | El frontend debe tener un **diseño responsive** (mobile-first) con Tailwind CSS | Alta |
| RF-04.2 | La UI debe incluir un **panel de chat** con mensajes del usuario y del agente | Alta |
| RF-04.3 | La UI debe mostrar las **fuentes citadas** en cada respuesta del agente | Alta |
| RF-04.4 | La UI debe incluir un **panel de carga de documentos** con drag-and-drop | Alta |
| RF-04.5 | La UI debe permitir **cambiar el provider activo** desde la configuración | Media |
| RF-04.6 | La UI debe mostrar **indicadores de carga y error** en todas las operaciones | Alta |
| RF-04.7 | La UI debe mostrar **estado de salud** de los providers | Media |

### Módulo RF-05: API REST

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-05.1 | `POST /chat` — Enviar mensaje y recibir respuesta (streaming SSE) | Alta |
| RF-05.2 | `POST /documents/upload` — Subir documento PDF/CSV | Alta |
| RF-05.3 | `DELETE /documents/{id}` — Eliminar documento y sus chunks | Alta |
| RF-05.4 | `GET /documents` — Listar documentos cargados | Alta |
| RF-05.5 | `GET /providers` — Listar providers con estado | Media |
| RF-05.6 | `POST /providers/switch` — Cambiar provider activo | Media |
| RF-05.7 | `GET /health` — Health check del sistema | Alta |

### Módulo RF-06: Integración n8n

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-06.1 | El backend debe exponer webhooks que n8n pueda consumir | Baja |
| RF-06.2 | n8n debe poder ejecutar workflows basados en eventos del agente | Baja |
| RF-06.3 | La integración con n8n debe ser **opcional** (no bloquea funcionalidad core) | Alta |

---

## 3. Requisitos No Funcionales

### RNF-01: Rendimiento

| ID | Requisito | Métrica |
|----|-----------|---------|
| RNF-01.1 | La ingesta de un documento PDF de 50 páginas no debe exceder 30 segundos | < 30s |
| RNF-01.2 | El tiempo de respuesta del chat (TTFT — time to first token) no debe exceder 3 segundos en condiciones normales | < 3s |
| RNF-01.3 | El sistema debe soportar al menos **10 usuarios concurrentes** en modo local | >= 10 |
| RNF-01.4 | La búsqueda semántica debe retornar resultados en < 500ms para colecciones de hasta 10,000 chunks | < 500ms |

### RNF-02: Disponibilidad y Resiliencia

| ID | Requisito |
|----|-----------|
| RNF-02.1 | Si un LLM provider falla, el sistema debe hacer failover a otro provider en < 5 segundos |
| RNF-02.2 | El sistema debe funcionar **sin conexión a internet** para la ingesta y búsqueda local (embeddings locales) |
| RNF-02.3 | El sistema no debe perder datos de documentos ingestados ante un reinicio (persistencia en disco) |

### RNF-03: Seguridad

| ID | Requisito |
|----|-----------|
| RNF-03.1 | Las API keys deben manejarse exclusivamente vía variables de entorno, nunca en código |
| RNF-03.2 | El backend debe validar el tamaño máximo de archivos subidos (default: 50MB) |
| RNF-03.3 | CORS debe restringirse a orígenes conocidos en producción |
| RNF-03.4 | Los archivos subidos deben ser sanitizados (validar extensión, MIME type) |

### RNF-04: Mantenibilidad

| ID | Requisito |
|----|-----------|
| RNF-04.1 | La cobertura de tests del backend debe ser >= 80% |
| RNF-04.2 | El código debe seguir el estilo definido por `ruff` (Python) y `prettier` (TypeScript) |
| RNF-04.3 | Cada provider LLM debe ser un módulo independiente y reemplazable |
| RNF-04.4 | El sistema debe usar logging estructurado con `loguru` para facilitar debugging |
| RNF-04.5 | La documentación de API debe generarse automáticamente vía OpenAPI |

### RNF-05: Portabilidad

| ID | Requisito |
|----|-----------|
| RNF-05.1 | El sistema debe ejecutarse con `docker compose up` sin configuración manual adicional |
| RNF-05.2 | El frontend debe funcionar en Chrome, Firefox, Safari y Edge (últimas 2 versiones) |
| RNF-05.3 | El sistema debe poder ejecutarse en Linux, macOS y Windows (vía Docker) |

---

## 4. Restricciones Técnicas

| ID | Restricción |
|----|-------------|
| RT-01 | **Tier gratuito**: Gemini Free (60 req/min), Groq Free (30 req/min, 6000 tokens/min) deben ser los providers por defecto |
| RT-02 | **Embeddings locales**: La ingesta debe funcionar sin API keys usando sentence-transformers |
| RT-03 | **Sin dependencias de nube**: El stack completo debe correr en localhost sin servicios externos (excepto LLM APIs) |
| RT-04 | **Python 3.12+**: No se admite Python < 3.12 |
| RT-05 | **React 19**: El frontend debe usar la última versión estable de React |

---

## 5. Criterios de Aceptación

1. **CA-01**: Usuario sube un PDF de 10 páginas → el sistema lo procesa y queda disponible para consultas.
2. **CA-02**: Usuario pregunta "¿Cuál es el tema principal del documento?" → el sistema responde con el contexto correcto citando fuente.
3. **CA-03**: El provider Gemini está caído → el sistema automáticamente usa Groq sin error visible para el usuario.
4. **CA-04**: Usuario hace 5 preguntas consecutivas → el sistema mantiene contexto de la conversación.
5. **CA-05**: La aplicación se levanta con `docker compose up` y está operativa en < 30 segundos.
6. **CA-06**: Usuario cambia el provider activo desde la UI → las siguientes respuestas usan el nuevo provider.
