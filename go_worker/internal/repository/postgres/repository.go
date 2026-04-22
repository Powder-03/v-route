package postgres

import (
	"context"
	"fmt"
	"log"

	"go_worker/internal/domain"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type TelemetryRepository struct {
	pool *pgxpool.Pool
}

// NewTelemetryRepository creates a new connected pgx pool.
func NewTelemetryRepository(ctx context.Context, dbURL string) (*TelemetryRepository, error) {
	config, err := pgxpool.ParseConfig(dbURL)
	if err != nil {
		return nil, fmt.Errorf("failed to parse config: %w", err)
	}

	pool, err := pgxpool.NewWithConfig(ctx, config)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to pool: %w", err)
	}

	// Verify connection
	if err := pool.Ping(ctx); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	return &TelemetryRepository{pool: pool}, nil
}

// BulkInsert uses PostgreSQL CopyFrom to batch insert a slice of TelemetryEvents
// natively, maximizing ingestion throughput.
func (r *TelemetryRepository) BulkInsert(ctx context.Context, events []domain.TelemetryEvent) error {
	if len(events) == 0 {
		return nil
	}

	rows := make([][]interface{}, 0, len(events))
	for _, event := range events {
		rows = append(rows, []interface{}{
			event.UserID,
			event.PromptTokens,
			event.ResponseTokens,
			event.LatencyMs,
			event.CacheHit,
		})
	}

	// Note: We omit "id" and "created_at" so PostgreSQL auto-generates them.
	insertedCount, err := r.pool.CopyFrom(
		ctx,
		pgx.Identifier{"telemetry_logs"},
		[]string{"user_id", "prompt_tokens", "response_tokens", "latency_ms", "cache_hit"},
		pgx.CopyFromRows(rows),
	)

	if err != nil {
		return fmt.Errorf("failed to execute CopyFrom batch insert: %w", err)
	}

	log.Printf("Successfully inserted batch of %d events using CopyFrom", insertedCount)
	return nil
}

func (r *TelemetryRepository) Close() {
	log.Println("Closing database connection pool...")
	r.pool.Close()
}
