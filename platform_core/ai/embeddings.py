"""
Embedding Providers and Vector Generation for pgvector similarity matching.
"""

import math
import hashlib
import re
from typing import List, Optional
import numpy as np
from platform_core.config import settings


class EmbeddingProvider:
    """
    Unified Embedding Generation Interface for pgvector similarity queries.
    Supports:
    1. OpenAI Embeddings (if OPENAI_API_KEY provided)
    2. Local Semantic Projection (deterministic 384-dimensional normalized vector)
    """

    DIMENSION = 384

    def __init__(self, provider: str = "auto"):
        self.provider = provider or settings.EMBEDDING_PROVIDER

    def get_embedding(self, text: str) -> List[float]:
        """Generate a 384-dimensional normalized unit vector for the given text."""
        if not text or not text.strip():
            return [0.0] * self.DIMENSION

        cleaned = text.strip()

        # Check OpenAI if key is present and requested
        if self.provider == "openai" and settings.OPENAI_API_KEY:
            try:
                import openai
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                resp = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=cleaned[:8000],
                    dimensions=self.DIMENSION
                )
                vec = resp.data[0].embedding
                return self._normalize(vec)
            except Exception as e:
                # Fallback to semantic projection
                pass

        return self._local_semantic_embedding(cleaned)

    def _local_semantic_embedding(self, text: str) -> List[float]:
        """
        Fast, deterministic semantic projection embedding generator.
        Generates a 384-dimensional normalized dense vector based on term frequencies,
        n-grams, domain keywords, and character trigram hashing.
        """
        vec = [0.0] * self.DIMENSION
        words = re.findall(r'[a-zA-Z0-9_\+#]+', text.lower())
        
        if not words:
            return vec

        # Weight key domain terms higher
        domain_weights = {
            "ai": 2.5, "ml": 2.5, "gis": 3.0, "satellite": 2.5, "radar": 2.5, "iot": 2.5,
            "sensor": 2.0, "vision": 2.0, "landslide": 3.0, "disaster": 2.5, "blockchain": 3.0,
            "security": 2.0, "cyber": 2.5, "health": 2.0, "biotech": 2.5, "agriculture": 2.5,
            "crop": 2.0, "water": 2.0, "flood": 2.5, "weather": 2.0, "robotics": 3.0,
            "drone": 2.5, "uav": 2.5, "hardware": 2.0, "software": 1.5, "react": 2.0,
            "fastapi": 2.0, "python": 1.5, "database": 1.8, "postgres": 2.0, "mobile": 1.8,
            "dashboard": 1.8, "prediction": 2.2, "alert": 2.0, "warning": 2.0, "detection": 2.0
        }

        for w in words:
            weight = domain_weights.get(w, 1.0)
            # Hash word into dimension index
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
            idx = h % self.DIMENSION
            sign = 1.0 if ((h >> 8) & 1) else -1.0
            vec[idx] += sign * weight

            # Also compute character trigrams for sub-word semantic capture
            if len(w) >= 3:
                for i in range(len(w) - 2):
                    trigram = w[i:i+3]
                    th = int(hashlib.sha256(trigram.encode("utf-8")).hexdigest()[:8], 16)
                    t_idx = th % self.DIMENSION
                    t_sign = 1.0 if ((th >> 4) & 1) else -1.0
                    vec[t_idx] += t_sign * 0.3 * weight

        return self._normalize(vec)

    @staticmethod
    def _normalize(vec: List[float]) -> List[float]:
        """L2 Normalize vector to unit length for cosine similarity."""
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0:
            return vec
        return [x / norm for x in vec]

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two vectors (returns 0.0 to 1.0)."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        # Clamp to [0, 1] range
        sim = max(0.0, min(1.0, (dot + 1.0) / 2.0))
        return sim
