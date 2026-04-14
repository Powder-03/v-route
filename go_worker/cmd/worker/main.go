package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"go_worker/internal/delivery/kafka"
	"go_worker/internal/domain"
	"go_worker/internal/repository/postgres"
	"go_worker/internal/usecase"
)

func getEnv(key, defaultVal string) string {
	if val, ok := os.LookupEnv(key); ok {
		return val
	}
	return defaultVal
}

func main() {
	// 1. Read Environment Variables
	kafkaBrokersStr := getEnv("KAFKA_BROKER", "localhost:9092")
	kafkaBrokers := strings.Split(kafkaBrokersStr, ",")
	kafkaGroupID := getEnv("KAFKA_GROUP_ID", "telemetry_consumer_group")
	dbURL := getEnv("DB_URL", "postgres://admin:secretpassword@localhost:5432/telemetry")
	topic := "gateway_telemetry"

	log.Println("Initializing go_worker microservice...")

	// 2. Setup Context for Graceful Shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// 3. Initialize Repository (PostgreSQL pgx pool)
	// We use a temporary context with timeout just for establishing the connection
	initCtx, initCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer initCancel()

	repo, err := postgres.NewTelemetryRepository(initCtx, dbURL)
	if err != nil {
		log.Fatalf("Failed to initialize PostgreSQL repository: %v", err)
	}
	defer repo.Close()

	// 4. Initialize Dependency: Usecase (Batch Orchestrator)
	worker := usecase.NewIngestionWorker(repo)

	// Channel for piping events from Kafka Delivery -> Worker Usecase
	// A buffered channel helps handle minor load spikes without blocking the Kafka consumer
	eventChan := make(chan domain.TelemetryEvent, 2000)

	// WaitGroup to wait for graceful shut down of component routines
	var wg sync.WaitGroup

	// 5. Start Usecase Batch Worker Goroutine
	wg.Add(1)
	go func() {
		defer wg.Done()
		worker.Run(ctx, eventChan)
	}()

	// 6. Initialize and Start Delivery Layer (Kafka Consumer Goroutine)
	consumer := kafka.NewConsumer(kafkaBrokers, kafkaGroupID, topic)
	defer consumer.Close()

	wg.Add(1)
	go func() {
		defer wg.Done()
		consumer.Start(ctx, eventChan)
	}()

	log.Println("Microservice successfully running and ready to ingest.")

	// 7. Wait for Stop Signal
	<-sigChan
	log.Println("Received termination signal, initiating graceful shutdown...")
	
	// Canceling the root context will immediately command the Kafka consumer loop to break.
	cancel() 
	
	// As the Kafka consumer breaks, it closes `eventChan`.
	// The `eventChan` closing signals the UseCase worker loop to exit and perform one final DB flush.
	// We wait on the WaitGroup until both loops are fully completed.
	wg.Wait()
	
	log.Println("Shutdown successfully complete. Exiting process.")
}
