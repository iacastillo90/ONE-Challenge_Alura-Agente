# 🤖 Agente de Inteligencia Artificial con RAG y Orquestación Multi-Provider LLM

<div align="center">

![Challenge ONE](https://img.shields.io/badge/Challenge%20ONE-AI%20FOR%20TECH-blue?style=for-the-badge&logo=alura)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19.0-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17%20%2B%20pgvector-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![n8n](https://img.shields.io/badge/n8n-Orchestration-FF6D5A?style=for-the-badge&logo=n8n&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)

**Desarrollado como proyecto principal para el Challenge ONE (Alura Latam)**  
*Una plataforma inteligente, resiliente y segura diseñada para la ingesta de conocimiento, consulta conversacional con RAG, conmutación por error entre modelos de lenguaje y automatizaciones en la nube.*

</div>

---

## 📖 Descripción General

Este proyecto consiste en un **agente conversacional empresarial impulsado por Inteligencia Artificial** que combina la potencia de la **Generación Aumentada por Recuperación (RAG)** con una arquitectura de **conmutación por error (fallback) entre múltiples proveedores de Modelos de Lenguaje (LLMs)**.

El sistema permite a las organizaciones e individuos cargar documentos en diversos formatos (PDF, CSV, TXT), indexar semánticamente su contenido en una base de datos vectorial de alto rendimiento (`pgvector`) y mantener conversaciones contextualizadas en tiempo real con respuestas transmitidas por flujo continuo (**Server-Sent Events - SSE**).

Con un enfoque empático, seguro y técnicamente robusto, el agente garantiza alta disponibilidad mediante rotación automática de proveedores (Google Gemini, Groq, DeepSeek, OpenAI-Compatible), protegiendo la información sensible mediante sanitización de datos personales (**PII**) y ofreciendo una integración sin fricciones con flujos de trabajo en **n8n** y canales como **WhatsApp**.

---

## ✨ Características Principales

- 🧠 **Pipeline RAG Semántico:** Fragmentación por tokens (`RecursiveCharacterTextSplitter`), generación de embeddings locales (`sentence-transformers/all-MiniLM-L6-v2`) o por API, e indexaciones vectoriales con similitud de coseno.
- 🔄 **Enrutamiento Multi-Provider de LLM:** Sistema de conmutación inteligente en tiempo real entre **Google Gemini Free**, **Groq**, **DeepSeek** y **OpenAI-Compatible**. Si un proveedor experimenta límites de cuota, latencia o errores 5xx, el sistema rota automáticamente al siguiente sin interrumpir al usuario.
- ⚡ **Respuestas en Tiempo Real (Streaming SSE):** Transmisión continua de tokens desde el backend FastAPI hacia el frontend React para una experiencia conversacional fluida.
- 🛡️ **Seguridad Empresarial & PII Scrubbing:** Filtro mediante expresiones regulares para enmascarar automáticamente tarjetas de crédito, correos electrónicos, números telefónicos y credenciales antes de ser retornados al cliente. Autenticación dual mediante JWT y API Keys.
- 🔗 **Orquestación con n8n & Webhooks:** Soporte completo para disparar flujos visuales externos y recibir mensajes entrantes de plataformas como WhatsApp.
- 📊 **Observabilidad y Métricas:** Middleware integrado para exportación de métricas compatibles con **Prometheus** e inspección de salud detallada (`/health`).
- 🎨 **Interfaz de Usuario Moderna:** Desarrollada con React 19, TypeScript, Tailwind CSS v4, Zustand y TanStack Query, ofreciendo modo oscuro, gestión de sesiones y precarga interactiva.

---

## 🏗️ Arquitectura del Sistema

```mermaid
flowchart TD
    subgraph Cliente ["💻 Capa de Cliente"]
        UI["React 19 + TypeScript (Vite)"]
        SSE["Suscriptor SSE / Axios JWT"]
    end

    subgraph Proxy ["🛡️ Proxy Reverso & Seguridad"]
        Caddy["Caddy Server (HTTPS / Rate Limit)"]
    end

    subgraph Backend ["⚙️ FastAPI Backend (Python 3.12)"]
        Auth["Middleware JWT / API Key"]
        Router["ProviderRouter (Circuit Breaker & Fallback)"]
        PII["Filtro de Seguridad PII"]
        RAG["Motor RAG (Ingesta & Recuperación)"]
    end

    subgraph VectorDB ["📦 Capa de Datos & Vectores"]
        PG["PostgreSQL 17 + pgvector"]
        Disk["Almacenamiento Local de Documentos"]
    end

    subgraph LLMs ["☁️ Proveedores de LLM"]
        Gemini["Google Gemini API (Principal)"]
        Groq["Groq API (Respaldo 1)"]
        DeepSeek["DeepSeek API (Respaldo 2)"]
        OpenAI["OpenAI Compatible (Respaldo 3)"]
    end

    subgraph Automation ["🤖 Orquestación Externa"]
        N8N["n8n Workflows / WhatsApp Webhooks"]
    end

    UI -->|HTTPS / WSS| Caddy
    Caddy --> Auth
    Auth --> RAG
    RAG -->|Consulta Vectorial| PG
    RAG --> Router
    Router -->|1° Intento| Gemini
    Router -.->|Fallback si falla| Groq
    Router -.->|Fallback si falla| DeepSeek
    Router -.->|Fallback si falla| OpenAI
    Router --> PII
    PII -->|Streaming SSE| SSE
    SSE --> UI
    Backend <-->|Webhooks HTTP| N8N
```

---

## 🛠️ Stack Tecnológico

### Backend
- **Lenguaje:** Python 3.12+
- **Framework:** FastAPI (asíncrono con Uvicorn)
- **Base de Datos & ORM:** PostgreSQL 17, `pgvector`, SQLAlchemy 2.0 (AsyncIO) y `asyncpg`
- **Embeddings:** `sentence-transformers` (`all-MiniLM-L6-v2`) para procesamiento local rápido
- **Procesamiento de Documentos:** PyMuPDF (`fitz`), Pandas, CSV
- **Logging & Métricas:** `loguru`, Prometheus Client Library

### Frontend
- **Framework:** React 19, TypeScript, Vite
- **Estilos:** Tailwind CSS v4, Lucide Icons
- **Gestión de Estado:** Zustand (para autenticación y chat)
- **Consultas HTTP:** Axios (con interceptores JWT), TanStack Query v5

### Infraestructura & DevOps
- **Contenedores:** Docker & Docker Compose
- **Proxy Reverso:** Caddy Server (configuración de cabeceras de seguridad y SSL automático)
- **Orquestador Visual:** n8n (para integración con WhatsApp y servicios externos)

---

## 🧠 Pipeline RAG y Búsqueda Vectorial

El flujo de procesamiento de conocimiento sigue los estándares más exigentes de la industria:

1. **Ingesta e Inspección:** El usuario sube un archivo (PDF, CSV o TXT). Se valida la firma de bytes (magic bytes `%PDF`) y el límite máximo de tamaño configurado.
2. **Chunking Semántico:** El texto extraído se procesa utilizando `RecursiveCharacterTextSplitter` parametrizado por número de tokens (tamaño por defecto: 512 tokens con solapamiento de 50 tokens).
3. **Generación de Embeddings:** Se generan vectores numéricos de 384 dimensiones usando `sentence-transformers` en local o la API de embeddings configurada.
4. **Indexación en `pgvector`:** Los vectores y sus metadatos asociados (nombre del documento, página, offset) se persisten en PostgreSQL con un índice IVFFlat / HNSW para consultas ultra rápidas.
5. **Recuperación y Re-escalado:** Al realizar una pregunta, la consulta se convierte a vector y se recuperan los $K$ fragmentos con mayor similitud de coseno, filtrados por umbral de calidad (`RETRIEVAL_SCORE_THRESHOLD`).

---

## 🔄 Enrutador Multi-Provider LLM y Fallback

Para mitigar caídas de servicio, bloqueos por cuota o latencias elevadas en APIs de terceros, el sistema incorpora la clase `ProviderRouter`:

```
               +-----------------------+
               | Petición de Respuesta |
               +-----------+-----------+
                           |
                           v
               +-----------------------+
               |  1. Google Gemini     | ---> ¿Éxito? ---> Retornar Stream
               +-----------+-----------+
                           | Fallo / Timeout / 429
                           v
               +-----------------------+
               |  2. Groq (Llama 3/Mixtral) ---> ¿Éxito? ---> Retornar Stream
               +-----------+-----------+
                           | Fallo / Timeout / 429
                           v
               +-----------------------+
               |  3. DeepSeek          | ---> ¿Éxito? ---> Retornar Stream
               +-----------+-----------+
                           | Fallo / Timeout / 429
                           v
               +-----------------------+
               | 4. OpenAI-Compatible  | ---> ¿Éxito? ---> Retornar Stream
               +-----------------------+
```

El router implementa un **Circuit Breaker**: tras 3 fallos consecutivos en un lapso breve, desactiva temporalmente el proveedor problemático por 60 segundos antes de reintentar su estado de salud.

---

## 🛡️ Seguridad, Autenticación y Filtro PII

- **Autenticación Dual:** Soporta tokens **JWT (JSON Web Tokens)** expirables con almacenamiento seguro de contraseñas mediante hashing (`passlib`/`bcrypt`) y autenticación basada en **API Keys** mediante la cabecera `X-API-Key`.
- **Filtro de Información Sensible (PII Scrubbing):** Las respuestas generadas por los modelos pasan por un pipeline de desinfección mediante expresiones regulares antes de salir del servidor:
  - 💳 Tarjetas de Crédito (Visa, Mastercard, AMEX)
  - 📧 Correos Electrónicos
  - 📞 Números Telefónicos Nacionales e Internacionales
  - 🪪 Documentos de Identidad (DNI/NIE/Pasaportes)
- **Path Traversal Shield:** Toda lectura o escritura en disco valida estrictamente la ruta canónica utilizando resolución de rutas relativas dentro de `UPLOAD_DIR`.

---

## ⚡ Orquestación y Webhooks (n8n & WhatsApp)

El sistema incluye soporte para la orquestación visual de procesos de negocio:

- **Recepciones Webhook (`/api/v1/webhooks/n8n`):** Permite a flujos de n8n enviar eventos o solicitar respuestas contextuales del agente.
- **Canal WhatsApp (`/api/v1/webhooks/whatsapp/send`):** Envío y recepción asíncrona de mensajes hacia la API de WhatsApp Cloud a través de nodos configurados en n8n.
- **Autenticación por Secreto Compartido:** Garantiza que únicamente las instancias autorizadas de n8n puedan interactuar con los endpoints de webhook mediante `N8N_WEBHOOK_SECRET`.

---

## 🚀 Instalación y Despliegue

### Requisitos Previos
- **Docker** 24.0+ y **Docker Compose** v2+
- **Git**
- *(Opcional para desarrollo local)* Python 3.12+ y Node.js 20+

### Despliegue Rápido con Docker Compose

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/tu-usuario/ONE-Challenge_Alura-Agente.git
   cd ONE-Challenge_Alura-Agente
   ```

2. **Configurar el archivo de entorno:**
   ```bash
   cp .env.example .env
   # Edita el archivo .env e ingresa al menos una API Key (ej. GEMINI_API_KEY)
   ```

3. **Iniciar la pila completa de servicios:**
   ```bash
   docker-compose up -d --build
   ```

4. **Acceder a las aplicaciones:**
   - 🌐 **Frontend (Interfaz de Usuario):** `http://localhost:5173` (o `http://app.one.localhost` con Caddy)
   - ⚙️ **Backend FastAPI Docs:** `http://localhost:8000/docs`
   - 🤖 **n8n Orchestrator:** `http://localhost:5678`

---

## ⚙️ Variables de Entorno

A continuación se resumen las variables clave del archivo `.env`:

| Variable | Descripción | Valor por Defecto |
| :--- | :--- | :--- |
| `DATABASE_URL` | URI de conexión a PostgreSQL con asyncpg | `postgresql+asyncpg://agent:agent@postgres:5432/agent` |
| `GEMINI_API_KEY` | Clave de API para Google Gemini | `""` |
| `GROQ_API_KEY` | Clave de API para Groq | `""` |
| `DEEPSEEK_API_KEY` | Clave de API para DeepSeek | `""` |
| `JWT_SECRET` | Clave secreta para la firma de tokens JWT | `change-me-in-production` |
| `EMBEDDING_PROVIDER` | Proveedor de embeddings (`local` o `api`) | `local` |
| `EMBEDDING_MODEL` | Modelo de embedding a utilizar | `all-MiniLM-L6-v2` |
| `MAX_UPLOAD_SIZE_MB` | Límite máximo para carga de archivos | `50` |
| `LLM_TIMEOUT_SECONDS` | Tiempo límite de espera por respuesta del LLM | `60` |

---

## 📊 Monitoreo y Observabilidad

El backend incluye instrumentalización integrada:

- **Endpoint de Salud (`GET /health`):** Retorna el estado en tiempo real de la conexión a la base de datos PostgreSQL, disponibilidad del almacenamiento vectorial y salud de los proveedores LLM.
- **Métricas Prometheus (`GET /metrics`):** Expone métricas de latencia de HTTP, conteo de peticiones por código de estado, tasa de fallback de LLMs y uso de memoria.
- **Registros Estructurados:** Implementados con `loguru` en formato JSON en entornos de producción para facilitar su ingesta en pilas ELK/Loki.

---

## 🧪 Ejecución de Pruebas

### Backend (Python)
Para ejecutar la suite completa de pruebas unitarias e integración:
```bash
cd backend
python -m pytest tests/ -v --cov=app
```

### Frontend (React)
Para verificar los componentes y hooks del cliente:
```bash
cd frontend
npm run test
```

---

## 🤝 Licencia y Reconocimientos

Este proyecto ha sido desarrollado con dedicación y rigor técnico como entrega para el **Challenge ONE AI FOR TECH** organizado por **Alura Latam** en alianza con **Oracle Next Education**.

Agradecimientos especiales a todo el equipo educativo de Alura Latam por promover el aprendizaje de tecnologías de vanguardia en Inteligencia Artificial y Desarrollo de Software.

---
<div align="center">
  <sub>Desarrollado con ❤️ para la comunidad de desarrolladores de América Latina.</sub>
</div>
