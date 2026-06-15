import uuid
import numpy as np
import logging
from redis.asyncio import Redis, from_url
from redis.commands.search.query import Query
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.field import VectorField, TextField

logger = logging.getLogger(__name__)

class CacheRepository:
    """
    Handles Vector Search integration with Redis.
    Uses FT.SEARCH and the Cosine Distance metric.
    """
    def __init__(self, redis_url: str, vector_dim: int):
        self.redis_url = redis_url
        self.client: Redis = None
        self.index_name = "prompts_idx"
        self.vector_dim = vector_dim

    async def connect(self):
        self.client = await from_url(self.redis_url)
        await self._ensure_index()

    async def _ensure_index(self):
        try:
            # Check if index already exists
            await self.client.ft(self.index_name).info()
            logger.info("Redis search index already exists.")
        except Exception:
            logger.info("Creating Redis vector search index...")
            schema = (
                TextField("prompt"),
                TextField("response"),
                VectorField("embedding", "FLAT", {
                    "TYPE": "FLOAT32",
                    "DIM": self.vector_dim,
                    "DISTANCE_METRIC": "COSINE"
                })
            )
            definition = IndexDefinition(prefix=["prompt:"], index_type=IndexType.HASH)
            await self.client.ft(self.index_name).create_index(fields=schema, definition=definition)

    async def search_similar(self, query_text: str, query_embedding: np.ndarray) -> list[dict]:
        """
        Executes a hybrid search: full-text match on 'prompt' combined with KNN vector search.
        Returns the top 5 candidates containing prompt, response, and vector_score.
        """
        import re
        # Clean text to alphanumeric words to avoid parser syntax errors
        words = re.findall(r'\w+', query_text)
        text_query = " | ".join(words) if words else "*"

        query_vector_bytes = query_embedding.tobytes()

        # Build Hybrid search: text match + KNN 5 vector search
        q = Query("(@prompt:$text_query)=>[KNN 5 @embedding $vec AS vector_score]")\
            .return_fields("prompt", "response", "vector_score")\
            .sort_by("vector_score")\
            .dialect(2)

        results = await self.client.ft(self.index_name).search(
            q, 
            query_params={"text_query": text_query, "vec": query_vector_bytes}
        )

        candidates = []
        for doc in results.docs:
            try:
                vector_score = float(doc.vector_score)
            except (TypeError, ValueError):
                vector_score = 1.0

            candidates.append({
                "prompt": getattr(doc, "prompt", ""),
                "response": getattr(doc, "response", ""),
                "vector_score": vector_score
            })
        
        return candidates

    async def save(self, prompt: str, response: str, embedding: np.ndarray):
        doc_id = f"prompt:{uuid.uuid4().hex}"
        
        # Save payload to a Redis Hash
        await self.client.hset(doc_id, mapping={
            "prompt": prompt,
            "response": response,
            "embedding": embedding.tobytes()
        })

    async def close(self):
        if self.client:
            await self.client.aclose()
