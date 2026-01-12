"""
Smart LLM Router for Digital Geoff (Zero-Cost Edition)

Routes requests to the cheapest capable model:
1. Groq (free, fast) - 14,400 requests/day, Llama 3.3 70B
2. Ollama (local, free) - Unlimited, runs on your hardware
3. Claude (paid fallback) - Only for complex tasks that others fail

This dramatically reduces costs while maintaining capability.
"""

import os
import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class ModelTier(Enum):
    """Model tiers ordered by cost (lowest first)."""
    FREE_FAST = "free_fast"      # Groq - free, very fast
    FREE_LOCAL = "free_local"    # Ollama - free, local
    PAID_SMART = "paid_smart"    # Claude - paid, smartest


class TaskComplexity(Enum):
    """Task complexity levels."""
    SIMPLE = "simple"        # Status checks, simple queries
    MODERATE = "moderate"    # Summaries, basic analysis
    COMPLEX = "complex"      # Multi-step reasoning, planning
    CRITICAL = "critical"    # High-stakes decisions, complex code


@dataclass
class ModelConfig:
    """Configuration for an LLM provider."""
    name: str
    tier: ModelTier
    model_id: str
    base_url: str
    api_key_env: str
    max_tokens: int = 4096
    requests_per_day: Optional[int] = None  # None = unlimited
    supports_tools: bool = True
    supports_vision: bool = False


@dataclass
class UsageTracker:
    """Track daily usage for rate-limited providers."""
    requests_today: int = 0
    last_reset: datetime = field(default_factory=datetime.utcnow)

    def increment(self):
        self._maybe_reset()
        self.requests_today += 1

    def can_use(self, limit: Optional[int]) -> bool:
        if limit is None:
            return True
        self._maybe_reset()
        return self.requests_today < limit

    def _maybe_reset(self):
        now = datetime.utcnow()
        if now.date() > self.last_reset.date():
            self.requests_today = 0
            self.last_reset = now


# Pre-configured models
MODELS = {
    "groq": ModelConfig(
        name="Groq",
        tier=ModelTier.FREE_FAST,
        model_id="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
        max_tokens=8192,
        requests_per_day=14400,  # Free tier limit
        supports_tools=True
    ),
    "groq_fast": ModelConfig(
        name="Groq Fast",
        tier=ModelTier.FREE_FAST,
        model_id="llama-3.1-8b-instant",
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
        max_tokens=8192,
        requests_per_day=14400,
        supports_tools=True
    ),
    "ollama": ModelConfig(
        name="Ollama Local",
        tier=ModelTier.FREE_LOCAL,
        model_id="mistral:latest",  # Or llama3.2, qwen2.5
        base_url="http://localhost:11434/v1",
        api_key_env="",  # No key needed for local
        max_tokens=4096,
        requests_per_day=None,  # Unlimited
        supports_tools=True
    ),
    "ollama_small": ModelConfig(
        name="Ollama Small",
        tier=ModelTier.FREE_LOCAL,
        model_id="qwen2.5:3b",  # Very fast, good for simple tasks
        base_url="http://localhost:11434/v1",
        api_key_env="",
        max_tokens=4096,
        requests_per_day=None,
        supports_tools=False
    ),
    "claude_haiku": ModelConfig(
        name="Claude Haiku",
        tier=ModelTier.PAID_SMART,
        model_id="claude-3-5-haiku-latest",
        base_url="https://api.anthropic.com",
        api_key_env="ANTHROPIC_API_KEY",
        max_tokens=4096,
        requests_per_day=None,
        supports_tools=True
    ),
    "claude_sonnet": ModelConfig(
        name="Claude Sonnet",
        tier=ModelTier.PAID_SMART,
        model_id="claude-sonnet-4-20250514",
        base_url="https://api.anthropic.com",
        api_key_env="ANTHROPIC_API_KEY",
        max_tokens=8192,
        requests_per_day=None,
        supports_tools=True,
        supports_vision=True
    )
}


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        max_tokens: int = 4096
    ) -> dict:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass


class GroqProvider(LLMProvider):
    """Groq API provider (OpenAI-compatible)."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.api_key = os.getenv(config.api_key_env, "")
        self.usage = UsageTracker()

    def is_available(self) -> bool:
        return bool(self.api_key) and self.usage.can_use(self.config.requests_per_day)

    async def complete(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        max_tokens: int = 4096
    ) -> dict:
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.model_id,
            "messages": messages,
            "max_tokens": min(max_tokens, self.config.max_tokens)
        }

        if tools and self.config.supports_tools:
            payload["tools"] = tools

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.config.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            self.usage.increment()
            return response.json()


class OllamaProvider(LLMProvider):
    """Ollama local provider (OpenAI-compatible API)."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        if self._available is None:
            # Check if Ollama is running
            import httpx
            try:
                response = httpx.get(
                    f"{self.config.base_url.replace('/v1', '')}/api/tags",
                    timeout=2.0
                )
                self._available = response.status_code == 200
            except Exception:
                self._available = False
        return self._available

    async def complete(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        max_tokens: int = 4096
    ) -> dict:
        import httpx

        payload = {
            "model": self.config.model_id,
            "messages": messages,
            "max_tokens": min(max_tokens, self.config.max_tokens),
            "stream": False
        }

        if tools and self.config.supports_tools:
            payload["tools"] = tools

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.config.base_url}/chat/completions",
                json=payload,
                timeout=120.0  # Local models can be slower
            )
            response.raise_for_status()
            return response.json()


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.api_key = os.getenv(config.api_key_env, "")

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def complete(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        max_tokens: int = 4096
    ) -> dict:
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)

        # Convert to Anthropic format
        system = None
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                anthropic_messages.append(msg)

        kwargs = {
            "model": self.config.model_id,
            "max_tokens": min(max_tokens, self.config.max_tokens),
            "messages": anthropic_messages
        }

        if system:
            kwargs["system"] = system

        if tools and self.config.supports_tools:
            kwargs["tools"] = self._convert_tools(tools)

        response = client.messages.create(**kwargs)

        # Convert back to OpenAI format for consistency
        return self._to_openai_format(response)

    def _convert_tools(self, openai_tools: list[dict]) -> list[dict]:
        """Convert OpenAI tool format to Anthropic format."""
        anthropic_tools = []
        for tool in openai_tools:
            if tool.get("type") == "function":
                func = tool["function"]
                anthropic_tools.append({
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {"type": "object", "properties": {}})
                })
        return anthropic_tools

    def _to_openai_format(self, response) -> dict:
        """Convert Anthropic response to OpenAI format."""
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input)
                    }
                })

        message = {"role": "assistant", "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls

        return {
            "choices": [{"message": message, "finish_reason": response.stop_reason}],
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens
            }
        }


class SmartRouter:
    """
    Intelligent LLM router that minimizes costs.

    Strategy:
    1. Classify task complexity
    2. Try cheapest capable model first
    3. Fall back to more capable models if needed
    4. Cache responses to avoid repeat calls
    """

    def __init__(self):
        self.providers: dict[str, LLMProvider] = {}
        self.cache: dict[str, dict] = {}  # Simple in-memory cache
        self.cache_ttl = timedelta(hours=1)
        self._init_providers()

    def _init_providers(self):
        """Initialize available providers."""
        # Free tier first
        if os.getenv("GROQ_API_KEY"):
            self.providers["groq"] = GroqProvider(MODELS["groq"])
            self.providers["groq_fast"] = GroqProvider(MODELS["groq_fast"])

        # Local (always try)
        self.providers["ollama"] = OllamaProvider(MODELS["ollama"])
        self.providers["ollama_small"] = OllamaProvider(MODELS["ollama_small"])

        # Paid fallback
        if os.getenv("ANTHROPIC_API_KEY"):
            self.providers["claude_haiku"] = ClaudeProvider(MODELS["claude_haiku"])
            self.providers["claude_sonnet"] = ClaudeProvider(MODELS["claude_sonnet"])

    def classify_complexity(self, messages: list[dict], tools: Optional[list[dict]]) -> TaskComplexity:
        """Classify task complexity to route to appropriate model."""
        # Get the user's message
        user_msg = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_msg = msg["content"].lower()
                break

        # Simple heuristics (can be improved with a classifier)
        simple_patterns = [
            "status", "what time", "list", "show me", "how many",
            "yes", "no", "ok", "thanks", "hello", "hi"
        ]

        complex_patterns = [
            "analyze", "compare", "explain why", "design", "architect",
            "strategy", "plan", "debug", "refactor", "optimize",
            "write code", "implement", "create a"
        ]

        critical_patterns = [
            "send email", "post message", "create task", "schedule",
            "delete", "cancel", "approve", "decide"
        ]

        # Check patterns
        if any(p in user_msg for p in critical_patterns):
            return TaskComplexity.CRITICAL

        if any(p in user_msg for p in complex_patterns):
            return TaskComplexity.COMPLEX

        if tools and len(tools) > 3:
            return TaskComplexity.COMPLEX

        if any(p in user_msg for p in simple_patterns):
            return TaskComplexity.SIMPLE

        if len(user_msg) < 50:
            return TaskComplexity.SIMPLE

        return TaskComplexity.MODERATE

    def get_routing_order(self, complexity: TaskComplexity, needs_tools: bool) -> list[str]:
        """Get ordered list of providers to try based on complexity."""
        if complexity == TaskComplexity.SIMPLE:
            # Fastest, cheapest first
            return ["groq_fast", "ollama_small", "groq", "ollama", "claude_haiku"]

        elif complexity == TaskComplexity.MODERATE:
            # Balance speed and capability
            return ["groq", "ollama", "groq_fast", "claude_haiku"]

        elif complexity == TaskComplexity.COMPLEX:
            # Need more capable models
            if needs_tools:
                return ["groq", "claude_haiku", "ollama", "claude_sonnet"]
            return ["groq", "ollama", "claude_haiku", "claude_sonnet"]

        else:  # CRITICAL
            # Use most reliable, even if paid
            return ["claude_haiku", "groq", "claude_sonnet"]

    def _cache_key(self, messages: list[dict]) -> str:
        """Generate cache key from messages."""
        content = json.dumps(messages, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    def _check_cache(self, key: str) -> Optional[dict]:
        """Check if we have a cached response."""
        if key in self.cache:
            cached = self.cache[key]
            if datetime.utcnow() - cached["timestamp"] < self.cache_ttl:
                return cached["response"]
            else:
                del self.cache[key]
        return None

    def _store_cache(self, key: str, response: dict):
        """Store response in cache."""
        self.cache[key] = {
            "response": response,
            "timestamp": datetime.utcnow()
        }
        # Limit cache size
        if len(self.cache) > 1000:
            oldest = min(self.cache.items(), key=lambda x: x[1]["timestamp"])
            del self.cache[oldest[0]]

    async def complete(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        max_tokens: int = 4096,
        force_provider: Optional[str] = None
    ) -> dict:
        """
        Route request to best available provider.

        Returns OpenAI-compatible response format.
        """
        # Check cache first (only for non-tool requests)
        if not tools:
            cache_key = self._cache_key(messages)
            cached = self._check_cache(cache_key)
            if cached:
                return cached

        # Classify and route
        complexity = self.classify_complexity(messages, tools)

        if force_provider and force_provider in self.providers:
            order = [force_provider]
        else:
            order = self.get_routing_order(complexity, bool(tools))

        last_error = None

        for provider_name in order:
            provider = self.providers.get(provider_name)
            if not provider or not provider.is_available():
                continue

            try:
                response = await provider.complete(messages, tools, max_tokens)

                # Cache successful responses (non-tool)
                if not tools:
                    self._store_cache(cache_key, response)

                # Add metadata about which provider was used
                response["_provider"] = provider_name
                response["_complexity"] = complexity.value

                return response

            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(f"All providers failed. Last error: {last_error}")

    def get_status(self) -> dict:
        """Get status of all providers."""
        status = {}
        for name, provider in self.providers.items():
            available = provider.is_available()
            status[name] = {
                "available": available,
                "tier": MODELS.get(name, MODELS.get(name.split("_")[0])).tier.value if name in MODELS or name.split("_")[0] in MODELS else "unknown"
            }
            if hasattr(provider, "usage"):
                status[name]["requests_today"] = provider.usage.requests_today
        return status


# Singleton router instance
_router: Optional[SmartRouter] = None


def get_router() -> SmartRouter:
    """Get or create the singleton router."""
    global _router
    if _router is None:
        _router = SmartRouter()
    return _router
