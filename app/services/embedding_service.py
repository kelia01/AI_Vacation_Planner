import os
from typing import List, Union
import numpy as np
import hashlib
import json
from pathlib import Path

class EmbeddingService:
    """
    Handles text embedding using sentence-transformers.
    Uses a local model to avoid API costs.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.cache_dir = Path(os.path.dirname(__file__)) / "embedding_cache"
        self.cache_dir.mkdir(exist_ok=True)
        
    def _load_model(self):
        """Lazy load the embedding model."""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                print(f"Loading embedding model: {self.model_name}")
                self.model = SentenceTransformer(self.model_name)
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required. Install with: "
                    "pip install sentence-transformers"
                )
        return self.model
    
    def _get_cache_key(self, text: str) -> str:
        """Generate a cache key for a text string."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def encode(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """
        Encode text(s) to embeddings.
        Returns list of embedding vectors.
        """
        model = self._load_model()
        
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            cache_file = self.cache_dir / f"{cache_key}.npy"
            
            if cache_file.exists():
                embedding = np.load(cache_file).tolist()
                embeddings.append(embedding)
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
                embeddings.append(None)
        
        if uncached_texts:
            new_embeddings = model.encode(
                uncached_texts,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            
            for idx, text in zip(uncached_indices, uncached_texts):
                embedding = new_embeddings[idx].tolist()
                cache_key = self._get_cache_key(text)
                cache_file = self.cache_dir / f"{cache_key}.npy"
                
                np.save(cache_file, np.array(embedding))
                embeddings[idx] = embedding
        
        return embeddings
    
    def encode_single(self, text: str) -> List[float]:
        """Encode a single text and return its embedding."""
        result = self.encode([text])
        return result[0]

# Singleton instance
embedding_service = EmbeddingService()