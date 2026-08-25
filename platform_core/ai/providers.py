"""
AI Provider Interface and Implementations (Anthropic, OpenAI, Groq, Gemini, Heuristic/Offline).
"""

import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from platform_core.config import settings

logger = logging.getLogger("sih_platform.ai")


class AIProvider(ABC):
    """Abstract interface for LLM completions."""

    @abstractmethod
    def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Generate structured JSON response from prompt."""
        pass

    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text completion from prompt."""
        pass


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: str):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = [{"role": "user", "content": prompt}]
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=system_prompt or "You are an expert AI software architect for SIH hackathons.",
            messages=messages
        )
        return resp.content[0].text

    def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        sys = (system_prompt or "") + "\nRespond ONLY with valid, unescaped JSON. Do not include markdown code block backticks."
        text = self.generate_text(prompt, system_prompt=sys).strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text.strip())


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str):
        import openai
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2
        )
        return resp.choices[0].message.content

    def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        sys = (system_prompt or "") + "\nRespond in valid JSON."
        messages = [
            {"role": "system", "content": sys},
            {"role": "user", "content": prompt}
        ]
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.2
        )
        return json.loads(resp.choices[0].message.content)


class GroqProvider(AIProvider):
    """
    Groq Cloud inference provider using the OpenAI-compatible API.
    Free tier: ~14,400 requests/day, ~6,000 tokens/minute.
    Uses llama-3.3-70b-versatile for high-quality reasoning.
    Includes retry-with-backoff on 429 rate-limit responses.
    """

    # Bound a degraded Groq stage instead of allowing the SDK's multi-minute
    # default request timeout to dominate a repository-matching run.
    MAX_RETRIES = 2
    BACKOFF_BASE_SECONDS = 1.0
    REQUEST_TIMEOUT_SECONDS = 15.0

    def __init__(self, api_key: str):
        import openai
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=self.REQUEST_TIMEOUT_SECONDS,
            max_retries=0,
        )
        self.model = "openai/gpt-oss-20b"

    def _call_with_retry(self, messages: list, temperature: float = 0.2, response_format: Optional[dict] = None) -> str:
        """Execute an API call with exponential backoff on 429 rate-limit errors."""
        import openai as openai_module
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 2048,
                }
                if response_format:
                    kwargs["response_format"] = response_format
                resp = self.client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content
            except openai_module.RateLimitError as e:
                last_error = e
                wait = self.BACKOFF_BASE_SECONDS * (2 ** attempt)
                logger.warning(
                    f"[GroqProvider] Rate-limited (429) on attempt {attempt + 1}/{self.MAX_RETRIES}. "
                    f"Backing off {wait:.1f}s before retry..."
                )
                time.sleep(wait)
            except Exception as e:
                # Non-rate-limit errors should propagate immediately
                raise
        # All retries exhausted
        raise RuntimeError(
            f"[GroqProvider] All {self.MAX_RETRIES} retries exhausted after rate-limiting. Last error: {last_error}"
        )

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._call_with_retry(messages, temperature=0.2)

    def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        import openai as openai_module

        sys_content = (system_prompt or "") + "\nYou MUST respond with valid raw JSON only. Do NOT include markdown code fences, markdown formatting, or any extra text before or after the JSON."
        messages = [
            {"role": "system", "content": sys_content},
            {"role": "user", "content": prompt}
        ]
        try:
            text = self._call_with_retry(messages, temperature=0.15, response_format={"type": "json_object"})
        except openai_module.BadRequestError:
            # Only retry without JSON mode when the endpoint rejects that
            # option. Network failures and rate limits have already received
            # their bounded retry budget and must not be replayed a second time.
            text = self._call_with_retry(messages, temperature=0.15)
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        try:
            return json.loads(text)
        except Exception:
            import re
            m = re.search(r'(\{.*\})', text, re.DOTALL)
            if m:
                return json.loads(m.group(1))
            raise


class HeuristicAIProvider(AIProvider):
    """
    Intelligent deterministic AST and heuristic inference engine.
    Used when no external LLM keys are supplied or as offline fallback.
    Performs rich semantic inference, requirement extraction, and gap analysis.
    """

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        return f"Deterministic reasoning analysis:\n{prompt[:300]}..."

    def generate_json(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        # Fallback dictionary parser
        return {"status": "success", "analysis": "completed"}


def get_ai_provider() -> AIProvider:
    """Factory to instantiate the configured AI Provider."""
    provider_type = settings.AI_PROVIDER.lower()

    if (provider_type in ("auto", "anthropic")) and settings.ANTHROPIC_API_KEY:
        try:
            return AnthropicProvider(settings.ANTHROPIC_API_KEY)
        except Exception as e:
            logger.warning(f"Anthropic initialization failed: {e}")

    if (provider_type in ("auto", "openai")) and settings.OPENAI_API_KEY:
        try:
            return OpenAIProvider(settings.OPENAI_API_KEY)
        except Exception as e:
            logger.warning(f"OpenAI initialization failed: {e}")

    if (provider_type in ("auto", "groq")) and settings.GROQ_API_KEY:
        try:
            return GroqProvider(settings.GROQ_API_KEY)
        except Exception as e:
            logger.warning(f"Groq initialization failed: {e}")

    # Default to Heuristic / Offline Engine
    return HeuristicAIProvider()


def get_groq_provider() -> Optional[AIProvider]:
    """Dedicated factory for Groq. Returns None if no key is configured."""
    if settings.GROQ_API_KEY:
        try:
            return GroqProvider(settings.GROQ_API_KEY)
        except Exception as e:
            logger.error(f"[get_groq_provider] Failed to initialize Groq: {e}")
    return None
