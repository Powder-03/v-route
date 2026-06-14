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
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.client: Redis = None
        self.index_name = "prompts_idx"
        self.vector_dim = 768 # Dimension size for text-embedding-004

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

    async def search_similar(self, query_embedding: np.ndarray, threshold: float = 0.95):
        # Redis uses Distance Metric. Cosine Distance = 1 - Cosine Similarity
        # A similarity >= 0.95 equates to a distance <= 0.05.
        
        query_vector_bytes = query_embedding.tobytes()

        # Build K-Nearest Neighbors (KNN 1) query finding nearest vector
        q = Query("*=>[KNN 1 @embedding $vec AS vector_score]")\
            .return_fields("response", "vector_score")\
            .sort_by("vector_score")\
            .dialect(2)

        results = await self.client.ft(self.index_name).search(q, query_params={"vec": query_vector_bytes})

        if results.docs:
            top_hit = results.docs[0]
            # Convert score back to similarity
            distance = float(top_hit.vector_score)
            similarity = 1.0 - distance
            
            if similarity >= threshold:
                return getattr(top_hit, "response", None)
        
        return None

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
