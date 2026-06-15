import logging
import asyncpg
from app.domain.models import UsageSummary

logger = logging.getLogger(__name__)

class TelemetryRepository:
    """
    Handles read operations for user telemetry logs from PostgreSQL database.
    """
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def get_user_usage(self, user_id: str) -> UsageSummary:
        query = """
            SELECT 
                COUNT(*) as total_requests,
                COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                COALESCE(SUM(response_tokens), 0) as response_tokens,
                COALESCE(AVG(latency_ms), 0.0) as avg_latency_ms
            FROM telemetry_logs
            WHERE user_id = $1;
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, user_id)
            
        total_requests = row["total_requests"] if row else 0
        prompt_tokens = row["prompt_tokens"] if row else 0
        response_tokens = row["response_tokens"] if row else 0
        avg_latency_ms = float(row["avg_latency_ms"]) if row else 0.0
        total_tokens = prompt_tokens + response_tokens

        return UsageSummary(
            user_id=user_id,
            total_requests=total_requests,
            prompt_tokens=prompt_tokens,
            response_tokens=response_tokens,
            total_tokens=total_tokens,
            avg_latency_ms=round(avg_latency_ms, 2)
        )
