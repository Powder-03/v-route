import numpy as np
from sentence_transformers import SentenceTransformer

class VectorEngine:
    """
    Wraps the sentence-transformers logic for converting string prompts
    into float32 vector embeddings normalized for Cosine Similarity calculations.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # The model is loaded synchronously upon initialization
        self.model = SentenceTransformer(model_name)

    def encode(self, text: str) -> np.ndarray:
        # Generate embeddings
        embedding = self.model.encode(text)
        
        # L2 Normalization ensures that inner product matches pure cosine similarity.
        # Required for standardized Vector Search behaviors.
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        # Return strictly as a float32 numpy array
        return embedding.astype(np.float32)
