package usecase

import (
	"context"
	"log"
	"time"

	"go_worker/internal/domain"
)

const (
	BatchSizeLimit = 500
	BatchTimeout   = 2 * time.Second
)

type Repository interface {
	BulkInsert(ctx context.Context, events []domain.TelemetryEvent) error
}

type IngestionWorker struct {
	repo Repository
}

func NewIngestionWorker(repo Repository) *IngestionWorker {
	return &IngestionWorker{repo: repo}
}

// Run starts the batching logic. It reads from inChan and writes to the DB 
// either when the BatchSizeLimit is reached, or when the BatchTimeout ticker fires.
func (w *IngestionWorker) Run(ctx context.Context, inChan <-chan domain.TelemetryEvent) {
	batch := make([]domain.TelemetryEvent, 0, BatchSizeLimit)
	ticker := time.NewTicker(BatchTimeout)
	defer ticker.Stop()

	log.Println("Starting background ingestion orchestrator...")

	for {
		select {
		case event, ok := <-inChan:
			if !ok {
				// Channel closed, process remaining items and exit
				w.flush(ctx, batch)
				log.Println("Ingestion worker stopped gracefully, flushed remaining items.")
				return
			}
			batch = append(batch, event)

			if len(batch) >= BatchSizeLimit {
				w.flush(ctx, batch)
				// Reset batch slice without reallocating
				batch = batch[:0]
				ticker.Reset(BatchTimeout)
			}

		case <-ticker.C:
			if len(batch) > 0 {
				w.flush(ctx, batch)
				batch = batch[:0]
			}
		}
	}
}

// flush wraps the repository insertion logic and provides a fallback context
// in case the main application context is already canceled during teardown.
func (w *IngestionWorker) flush(ctx context.Context, batch []domain.TelemetryEvent) {
	if len(batch) == 0 {
		return
	}
	
	// Create a new distinct timeout so we can still flush during Graceful Shutdown
	// even if the root context is canceled.
	flushCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	log.Printf("Triggering repository write for %d events...", len(batch))
	if err := w.repo.BulkInsert(flushCtx, batch); err != nil {
		log.Printf("Failed to batch insert to postgres: %v\n", err)
	}
}
