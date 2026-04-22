package domain

// TelemetryEvent represents a single telemetry log from the API Gateway.
// It maps directly to the Kafka payload in JSON and the PostgreSQL schema.
type TelemetryEvent struct {
	UserID         string `json:"user_id"`
	PromptTokens   int    `json:"prompt_tokens"`
	ResponseTokens int    `json:"response_tokens"`
	LatencyMs      int    `json:"latency_ms"`
	CacheHit       bool   `json:"cache_hit"`
}
