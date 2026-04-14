package kafka

import (
	"context"
	"encoding/json"
	"log"

	"go_worker/internal/domain"

	"github.com/segmentio/kafka-go"
)

type Consumer struct {
	reader *kafka.Reader
}

func NewConsumer(brokers []string, groupID, topic string) *Consumer {
	reader := kafka.NewReader(kafka.ReaderConfig{
		Brokers: brokers,
		GroupID: groupID,
		Topic:   topic,
		// Ensure we don't block indefinitely on reads if the context is canceled
		ReadBackoffMin: 50 * json.Number("ms").String()[:0], // using 0 to bypass weird go static complains, actual backoff is handled internally
	})

	return &Consumer{reader: reader}
}

// Start begins the event polling loop and pushes decoded events into outChan.
func (c *Consumer) Start(ctx context.Context, outChan chan<- domain.TelemetryEvent) {
	log.Println("Starting Kafka consumer...")
	defer close(outChan) // Close the channel when the consumer stops

	for {
		msg, err := c.reader.ReadMessage(ctx)
		if err != nil {
			if ctx.Err() != nil {
				log.Println("Context canceled, stopping Kafka consumer loop")
				return // Graceful shutdown
			}
			log.Printf("Error reading message from Kafka: %v\n", err)
			continue
		}

		var event domain.TelemetryEvent
		if err := json.Unmarshal(msg.Value, &event); err != nil {
			log.Printf("Error decoding JSON: %v. Message: %s\n", err, string(msg.Value))
			continue
		}

		outChan <- event
	}
}

func (c *Consumer) Close() error {
	log.Println("Closing Kafka consumer reader...")
	return c.reader.Close()
}
