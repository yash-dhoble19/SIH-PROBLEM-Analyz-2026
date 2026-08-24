"""
AI and Embeddings subsystem package.
"""

from platform_core.ai.providers import AIProvider, get_ai_provider
from platform_core.ai.embeddings import EmbeddingProvider

__all__ = ["AIProvider", "get_ai_provider", "EmbeddingProvider"]
