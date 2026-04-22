# OptiPrompt go_worker Microservice

A high-speed background telemetry ingestion engine written in Go using clean architecture.

## Architecture Highlights
- Uses **Goroutines and Channels** to detach reading Kafka topics from DB I/O.
- Uses **pgx/v5 `CopyFrom`** protocol to dramatically improve mass row insertion speeds.
- Uses time-based and count-based triggers to ensure maximum throughput with capped latency.

## Initialization

First, configure dependencies by downloading them:
```bash
go mod tidy
```

## Running Locally

Set up environment variables and run:
```bash
export KAFKA_BROKER=localhost:9092
export KAFKA_GROUP_ID=telemetry_consumer_group
export DB_URL=postgres://admin:secretpassword@localhost:5432/telemetry

go run cmd/worker/main.go
```

## Docker Environment Context

The worker is designed to integrate into the `optiprompt-net` bridge network via `docker-compose`. 

Example addition to your `docker-compose.yaml` (do not commit this block to go_worker directory, just use for reference):
```yaml
  go_worker:
    build: 
      context: ./go_worker
    environment:
      - KAFKA_BROKER=kafka_broker:9092
      - KAFKA_GROUP_ID=telemetry_consumer_group
      - DB_URL=postgres://admin:secretpassword@postgres_db:5432/telemetry
    networks:
      - optiprompt-net
    depends_on:
      - kafka_broker
      - postgres_db
```
