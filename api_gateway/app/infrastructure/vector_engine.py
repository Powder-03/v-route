import numpy as np
from google import genai

class VectorEngine:
    """
    Wraps the google-genai logic for converting string prompts
    into float32 vector embeddings normalized for Cosine Similarity calculations.
    """
    def __init__(self, model_name: str = "text-embedding-004"):
        # The client automatically picks up the GEMINI_API_KEY environment variable
        self.client = genai.Client()
        self.model_name = model_name

    def encode(self, text: str) -> np.ndarray:
        # Generate embeddings using the Google Gemini model
        response = self.client.models.embed_content(
            model=self.model_name,
            contents=text,
        )
        
        # Extract the list of floats and cast to numpy array natively
        embedding = np.array(response.embeddings[0].values, dtype=np.float32)
        
        # L2 Normalization ensures that inner product matches pure cosine similarity.
        # Required for standardized Vector Search behaviors.
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding
