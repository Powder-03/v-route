-- Auto-executed on PostgreSQL 15 container boot if placed in /docker-entrypoint-initdb.d/

-- Create master partitioned table
CREATE TABLE telemetry_logs (
    log_id UUID DEFAULT gen_random_uuid() NOT NULL,
    user_id VARCHAR NOT NULL,
    prompt_tokens INT,
    response_tokens INT,
    latency_ms INT,
    cache_hit BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
) PARTITION BY HASH (user_id);

-- Create exact 4 physical shards mapping MODULUS
CREATE TABLE telemetry_shard_0 PARTITION OF telemetry_logs FOR VALUES WITH (MODULUS 4, REMAINDER 0);
CREATE TABLE telemetry_shard_1 PARTITION OF telemetry_logs FOR VALUES WITH (MODULUS 4, REMAINDER 1);
CREATE TABLE telemetry_shard_2 PARTITION OF telemetry_logs FOR VALUES WITH (MODULUS 4, REMAINDER 2);
CREATE TABLE telemetry_shard_3 PARTITION OF telemetry_logs FOR VALUES WITH (MODULUS 4, REMAINDER 3);

-- Add index to partition key for fast lookup mappings
CREATE INDEX idx_telemetry_logs_user_id ON telemetry_logs (user_id);
