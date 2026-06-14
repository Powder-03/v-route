import os
import logging
import numpy as np
from litellm import aembedding

logger = logging.getLogger(__name__)

class VectorEngine:
    """
    Wraps LiteLLM logic for converting string prompts
    into float32 vector embeddings normalized for Cosine Similarity calculations.
    Queries the API dynamically on startup to determine dimension sizes.
    """
    def __init__(self, model_name: str = None):
        if model_name is None:
            model_name = os.getenv("EMBEDDING_MODEL", "gemini/text-embedding-004")
        self.model_name = model_name
        self.dimension_size = 768  # Fallback default value

    async def probe_dimension(self):
        """
        Runs a quick warmup request to determine the output dimension size of the embedding model.
        """
        try:
            logger.info(f"Probing embedding model '{self.model_name}' to check dimension size...")
            response = await aembedding(model=self.model_name, input=["warmup"])
            embedding_values = response["data"][0]["embedding"]
            self.dimension_size = len(embedding_values)
            logger.info(f"Successfully determined dimension size: {self.dimension_size}")
        except Exception as e:
            logger.warning(f"Embedding model probe failed ({e}). Falling back to default dimensions.")
            # Fallback mappings for standard models
            if "text-embedding-3-small" in self.model_name:
                self.dimension_size = 1536
            elif "text-embedding-3-large" in self.model_name:
                self.dimension_size = 3072
            elif "all-MiniLM-L6-v2" in self.model_name:
                self.dimension_size = 384
            else:
                self.dimension_size = 768

    async def encode(self, text: str) -> np.ndarray:
        # Generate embedding via LiteLLM API
        response = await aembedding(model=self.model_name, input=[text])
        embedding = np.array(response["data"][0]["embedding"], dtype=np.float32)
        
        # L2 Normalization ensures that inner product matches pure cosine similarity.
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding
