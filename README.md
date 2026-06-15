# v-route: Intelligent Semantic Caching & Telemetry Gateway

`v-route` is a high-performance, cost-effective, and fully dockerized API gateway middleware designed for Large Language Models (LLMs). It leverages LiteLLM for both universal LLM routing and cloud-based dynamic embeddings, using Redis Vector Search to semantically cache LLM prompts. This setup avoids heavy local deep-learning environments (like PyTorch) inside the gateway container while keeping the system model-agnostic. Telemetry logs (token count, cache performance, and latency) are processed asynchronously via Apache Kafka and a Go-based worker process into a partitioned PostgreSQL database.

---

## 🏗️ System Architecture

```mermaid
graph TD
    Client[Client Browser / Consumer] -->|HTTP POST /generate| Nginx[Nginx Reverse Proxy]
    Nginx -->|Proxy Pass| FastAPI[FastAPI Gateway]
    
    subgraph API Gateway Services
        FastAPI -->|1. Generate Embedding| EmbedAPI[LiteLLM Embedding API]
        FastAPI -->|2. Search / Save Vectors| Redis[Redis Stack Vector DB]
        FastAPI -->|3. Fallback Completion| LLM[Universal LLMs via LiteLLM]
        FastAPI -->|4. Publish Telemetry| Kafka[Kafka Broker]
    end

    subgraph Background Telemetry Ingestion
        Kafka -->|5. Consume Stream| GoWorker[Go Ingestion Worker]
        GoWorker -->|6. Batch pgx Copy| Postgres[(Partitioned Postgres DB)]
    end
```

### Flow Walkthrough

1. **Client Request**: The client requests a generation endpoint by hitting `POST /generate`.
2. **Reverse Proxy (Nginx)**: Nginx routes the request to the FastAPI app cluster.
3. **Embedding Vectorization**: The FastAPI Gateway calls LiteLLM's embedding API (configurable via `EMBEDDING_MODEL`, e.g., `gemini/gemini-embedding-2`) to convert the prompt into a normalized (L2) float vector. To prevent hardcoding, the dimension is automatically probed on startup via a test request and the Redis index schema is updated dynamically.
4. **Semantic Caching**:
   - The Gateway executes a K-Nearest Neighbors (KNN) vector search in **Redis Stack** using the Cosine distance metric.
   - If the similarity is `> 95%` (equivalent to a cosine distance of `< 0.05`), it instantly serves the cached response, setting `cache_hit: true`.
   - If there is a cache miss, the gateway routes the fallback completion request to the downstream LLM using `litellm` (configurable via `LLM_MODEL`, e.g., `gemini/gemini-1.5-flash`), returns the response, and registers the prompt/embedding asynchronously back into Redis.
5. **Asynchronous Telemetry Stream**: The Gateway formats a telemetry log containing token count, latency in milliseconds, and cache performance. This event is handed off to an asynchronous task that publishes it to the `gateway_telemetry` topic on **Apache Kafka** without blocking the HTTP client's response.
6. **Data Ingestion**: A high-speed telemetry ingestion service written in **Go** consumes from Kafka. The worker processes and holds messages, using a time-capped / count-capped queue, before mass-loading them into **PostgreSQL** using the fast `CopyFrom` protocol.
7. **Sharded Telemetry Storage**: PostgreSQL partitions the logs into 4 sharded physical tables (`telemetry_shard_0` through `telemetry_shard_3`) via a hash of the `user_id`.

---

## 🛠️ Technology Stack

* **Reverse Proxy**: Nginx (configured with API proxy connection timeouts and security headers).
* **API Framework**: FastAPI (Python 3.11-slim) using standard clean architecture.
* **Vector Embeddings**: LiteLLM Embeddings (supports any API embedding model like `gemini/gemini-embedding-2` or `openai/text-embedding-3-small`, with dynamically probed output dimensions at startup).
* **Vector Cache**: Redis Stack Server (dynamically configured dimension sizes based on the probed embedding model, using HASH indices with Flat Index Vector Search + Cosine similarity).
* **LLM Routing Factory**: LiteLLM (supports model-agnostic completions to OpenAI, Gemini, Anthropic, etc.).
* **Streaming Engine**: Apache Kafka (KRaft mode).
* **Data Processing Worker**: Go (pgx/v5 driver, context-based graceful shutdowns, and bulk copying).
* **Database**: PostgreSQL 15 (Hash partitioned logging).

---

## 📂 Project Structure

```
v-route/
├── api_gateway/              # FastAPI Application Code
│   ├── app/
│   │   ├── api/              # API router & request schemas
│   │   ├── domain/           # Core domain models
│   │   ├── infrastructure/   # Vector engine (Gemini), Redis cache, and Kafka brokers
│   │   └── usecases/         # Business orchestrators (GenerateUseCase)
│   ├── Dockerfile
│   ├── main.py               # Gateway entrypoint & lifecycle management
│   └── requirements.txt
├── go_worker/                # High-speed telemetry ingestion worker
│   ├── cmd/worker/main.go    # Application entry point
│   ├── internal/             # Clean Architecture implementation (Delivery, Domain, Repo, Usecase)
│   ├── Dockerfile
│   └── README.md
├── nginx/
│   └── nginx.conf            # Gateway routing & security configuration
├── postgres/
│   └── init.sql              # Database initialization & hash partitioning rules
├── .env.example              # Template for environment variables
└── docker-compose.yaml       # Master orchestration compose file
```

---

## 🚀 Getting Started

### 📋 Prerequisites

* **Docker** & **Docker Compose**
* **Model API Keys** (e.g. Google Gemini API Key, OpenAI API Key, or Anthropic API Key depending on target models)

### ⚙️ Configuration

1. Clone the repository and navigate to the project directory:
   ```bash
   cd v-route
   ```

2. Create a `.env` file from the provided `.env.example`:
   ```bash
   copy .env.example .env
   ```
   *(On Unix systems, use `cp .env.example .env`)*

3. Open `.env` and configure your models and credentials:
   ```env
   POSTGRES_USER=admin
   POSTGRES_PASSWORD=secretpassword
   POSTGRES_DB=telemetry
   
   # Model Configurations
   EMBEDDING_MODEL=gemini/gemini-embedding-2
   LLM_MODEL=gemini/gemini-1.5-flash
   
   # Provider API Keys
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   OPENAI_API_KEY=your_actual_openai_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

### 🐳 Starting the Application Stack

Run the following command to build and launch all services in the background:

```bash
docker-compose up --build -d
```

Docker Compose will provision:
* `nginx`: Port `80` (re-routes `http://localhost/` to `http://localhost/docs` and proxies general requests).
* `fastapi_worker_1`: Port `8000` (internal service).
* `redis_cache`: Redis Stack container with vector capabilities.
* `kafka_broker`: Single KRaft broker for messaging.
* `postgres_db`: Database with table partition pre-configuration.
* `golang_worker`: Background service reading Kafka and writing to Postgres.

Verify that all services are healthy:
```bash
docker-compose ps
```

---

## 🧪 Local API Testing

Once running, the interactive OpenAPI documentation is available at:
* **Interactive Swagger UI**: [http://localhost/docs](http://localhost/docs)

### Post a Generate Request
You can test semantic caching by sending requests using `curl` or any API client.

#### First Request (Cache Miss)
```bash
curl -X POST "http://localhost/generate" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "user_123", "prompt": "Explain the theory of relativity in simple terms."}'
```
**Response**:
```json
{
  "response": "[LLM generated] Response to: Explain the theory of relativity in simple terms.",
  "cache_hit": false
}
```

#### Second Request (Cache Hit)
Send a prompt that is semantically similar:
```bash
curl -X POST "http://localhost/generate" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "user_123", "prompt": "Can you explain the theory of relativity simply?"}'
```
**Response**:
```json
{
  "response": "[LLM generated] Response to: Explain the theory of relativity in simple terms.",
  "cache_hit": true
}
```
Notice that `cache_hit` is now `true` and the original response was served instantly without contacting the LLM.

---

## 🛠️ Local Development Setup (Run without Docker Compose)

If you are developing components and want to run them outside of containers, follow these setups:

### 1. Redis, Kafka, and PostgreSQL Dependencies
It is recommended to run the data stores using Docker:
```bash
# Start only the databases & messaging brokers
docker-compose up redis_cache kafka_broker postgres_db -d
```

### 2. Run API Gateway Locally
Navigate to `/api_gateway`, install requirements, set environments, and start the app:
```bash
cd api_gateway
python -m venv venv
# Activate on Windows:
.\venv\Scripts\activate
# Activate on Unix:
source venv/bin/activate

pip install -r requirements.txt

# Set temporary environment flags
set EMBEDDING_MODEL=gemini/gemini-embedding-2
set LLM_MODEL=gemini/gemini-1.5-flash
set GEMINI_API_KEY=your_gemini_api_key_here
set OPENAI_API_KEY=your_openai_api_key_here
set ANTHROPIC_API_KEY=your_anthropic_api_key_here
set REDIS_URL=redis://localhost:6379/0
set KAFKA_BROKER=localhost:9092

# Start development server
uvicorn main:app --reload --port 8000
```

### 3. Run Go Worker Locally
Navigate to `/go_worker`, fetch dependencies, and execute the consumer:
```bash
cd go_worker
go mod tidy

# Set environment overrides
# Windows cmd:
set KAFKA_BROKER=localhost:9092
set DB_URL=postgres://admin:secretpassword@localhost:5432/telemetry

# Run
go run cmd/worker/main.go
```

---

## 📊 Telemetry Database Partitioning

The system utilizes partitioned tables to support large volumes of log files. Telemetry logs are stored in `telemetry_logs` which uses a **Hash Partition** on the `user_id` column.

```sql
CREATE TABLE telemetry_logs (
    log_id UUID DEFAULT gen_random_uuid() NOT NULL,
    user_id VARCHAR NOT NULL,
    prompt_tokens INT,
    response_tokens INT,
    latency_ms INT,
    cache_hit BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
) PARTITION BY HASH (user_id);
```

Behind the scenes, Postgres shards data across four tables automatically based on user ID:
* `telemetry_shard_0`
* `telemetry_shard_1`
* `telemetry_shard_2`
* `telemetry_shard_3`

This structure distributes telemetry queries and write IO operations evenly across multiple partitions.

---

## 🔒 Security Best Practices

* **Port Access Controls**: Only port `80` (Nginx reverse proxy) is exposed to the outside network. Backend infrastructure ports (Redis: `6379`, Kafka: `9092`, Postgres: `5432`, Uvicorn: `8000`) are accessible only inside the bridged `optiprompt-net` network.
* **HTTP Security Headers**: Nginx is configured to inject security headers including `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, and `Strict-Transport-Security`.
* **Non-Root Containers**: Dockerfiles are structured to run code as non-root users (`appuser` in the API gateway, scratch environment in the Go worker) where possible to lower execution permissions.
