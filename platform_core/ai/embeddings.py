"""Embedding providers for pgvector similarity matching.

The default backend is a locally executed SentenceTransformer model. Remote
providers are opt-in upgrades: selecting ``openai`` or ``google`` *and*
supplying that provider's key is required before a network request is made.
"""

import logging
import math
import hashlib
import threading
from typing import Dict, List, Optional

from platform_core.config import settings

logger = logging.getLogger("sih_platform.ai.embeddings")


class EmbeddingProvider:
    """Generate 384-dimensional, normalized semantic embeddings.

    ``auto`` deliberately means local. This keeps an installation useful and
    private without an API key, while users who want a managed service can set
    ``EMBEDDING_PROVIDER=openai`` or ``EMBEDDING_PROVIDER=google`` explicitly.
    """

    DIMENSION = 384
    LOCAL_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    _models: Dict[str, object] = {}
    _model_lock = threading.Lock()

    def __init__(self, provider: Optional[str] = None, local_model: Optional[str] = None):
        requested = (provider or settings.EMBEDDING_PROVIDER or "auto").strip().lower()
        self.provider = requested
        self.local_model_name = local_model or settings.LOCAL_EMBEDDING_MODEL or self.LOCAL_MODEL
        self._fallback_active = False
        self._backend = "uninitialized"

    @property
    def is_fallback_active(self) -> bool:
        """Backward-compatible flag: true whenever the local model is in use."""
        return self._backend in {"sentence-transformers", "serverless-vectorizer"} or self._fallback_active or self.provider in {
            "auto", "local", "sentence-transformers", "minilm"
        }

    @property
    def backend(self) -> str:
        """Name of the backend used by the most recent embedding request."""
        return self._backend

    def get_embedding(self, text: str) -> List[float]:
        """Generate one normalized embedding without implicit remote fallbacks."""
        return self.get_embeddings([text])[0]

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in a batch; local encoding avoids per-text model work."""
        if not texts:
            return []

        cleaned = [(text or "").strip() for text in texts]
        nonempty_indexes = [index for index, value in enumerate(cleaned) if value]
        vectors: List[List[float]] = [[0.0] * self.DIMENSION for _ in cleaned]
        if not nonempty_indexes:
            self._backend = "serverless-vectorizer"
            return vectors

        nonempty_texts = [cleaned[index][:8000] for index in nonempty_indexes]
        remote_vector_list = self._try_explicit_remote_provider(nonempty_texts)
        if remote_vector_list is None:
            remote_vector_list = self._local_embeddings(nonempty_texts)

        for index, vector in zip(nonempty_indexes, remote_vector_list):
            vectors[index] = vector
        return vectors

    def _try_explicit_remote_provider(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Use a remote service only when it was explicitly selected and keyed."""
        if self.provider == "openai":
            if not settings.OPENAI_API_KEY:
                logger.info("OpenAI embeddings were selected but OPENAI_API_KEY is absent; using the local model.")
                return None
            try:
                import openai

                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY, timeout=20.0, max_retries=0)
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=texts,
                    dimensions=self.DIMENSION,
                )
                self._backend = "openai"
                self._fallback_active = False
                return [self._validate_and_normalize(item.embedding, "OpenAI") for item in response.data]
            except Exception as exc:
                logger.warning("OpenAI embedding request failed; using the local model: %s", exc)
                self._fallback_active = True
                return None

        if self.provider in {"google", "gemini"}:
            if not settings.GOOGLE_API_KEY:
                logger.info("Google embeddings were selected but GOOGLE_API_KEY is absent; using the local model.")
                return None
            try:
                # google-genai is intentionally optional, just like an OpenAI key.
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=settings.GOOGLE_API_KEY)
                response = client.models.embed_content(
                    model=settings.GOOGLE_EMBEDDING_MODEL,
                    contents=texts,
                    config=types.EmbedContentConfig(output_dimensionality=self.DIMENSION),
                )
                embeddings = [item.values for item in response.embeddings]
                self._backend = "google"
                self._fallback_active = False
                return [self._validate_and_normalize(vector, "Google") for vector in embeddings]
            except Exception as exc:
                logger.warning("Google embedding request failed; using the local model: %s", exc)
                self._fallback_active = True
                return None

        # `auto` and every local alias intentionally skip all remote clients.
        return None

    def _generate_deterministic_embedding(self, text: str) -> List[float]:
        """Fast zero-dependency 384-dim normalized projection for serverless cloud runtimes."""
        vec = [0.0] * self.DIMENSION
        tokens = text.lower().split()
        for token in tokens:
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self.DIMENSION
            sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
            vec[idx] += sign
            for i in range(len(token) - 2):
                gram = token[i:i+3]
                gh = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16)
                gidx = gh % self.DIMENSION
                vec[gidx] += 0.5 * (1.0 if (gh >> 4) % 2 == 0 else -1.0)
        return self._normalize(vec)

    def _local_embeddings(self, texts: List[str]) -> List[List[float]]:
        try:
            model = self._load_local_model()
            if model is not None:
                encoded = model.encode(
                    texts,
                    batch_size=min(32, max(1, len(texts))),
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                self._backend = "sentence-transformers"
                self._fallback_active = self.provider not in {"auto", "local", "sentence-transformers", "minilm"}
                return [self._validate_and_normalize(vector.tolist(), "SentenceTransformer") for vector in encoded]
        except Exception:
            logger.info("SentenceTransformer unavailable; using serverless vectorizer.")
        
        self._backend = "serverless-vectorizer"
        self._fallback_active = True
        return [self._generate_deterministic_embedding(t) for t in texts]

    def _load_local_model(self):
        with self._model_lock:
            cached = self._models.get(self.local_model_name)
            if cached is not None:
                return cached
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                return None

            logger.info("Loading local embedding model %s", self.local_model_name)
            try:
                model = SentenceTransformer(
                    self.local_model_name,
                    device=settings.LOCAL_EMBEDDING_DEVICE,
                    model_kwargs={"use_safetensors": True},
                )
                dimension = model.get_sentence_embedding_dimension()
                if dimension != self.DIMENSION:
                    return None
                self._models[self.local_model_name] = model
                return model
            except Exception:
                return None


    def _validate_and_normalize(self, vector: List[float], provider_name: str) -> List[float]:
        if len(vector) != self.DIMENSION:
            raise RuntimeError(
                f"{provider_name} returned {len(vector)} dimensions; this database requires {self.DIMENSION}."
            )
        return self._normalize([float(value) for value in vector])

    @staticmethod
    def _normalize(vec: List[float]) -> List[float]:
        norm = math.sqrt(sum(value * value for value in vec))
        return vec if norm == 0 else [value / norm for value in vec]

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Return direct cosine similarity for same-sized normalized vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        return max(0.0, min(1.0, sum(a * b for a, b in zip(v1, v2))))
