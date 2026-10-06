"""
LLM Provider Abstraction Layer
Supports Mock, OpenAI, Anthropic, Azure OpenAI, and Ollama.
Switch providers via config/llm_providers.yaml — no code changes.
"""

import logging
import os
import re
from abc import ABC, abstractmethod


log = logging.getLogger(__name__)

_REASONING_BLOCK = re.compile(r"<think>.*?</think>", flags=re.DOTALL | re.IGNORECASE)


def strip_reasoning(text: str) -> str:
    """Remove <think>…</think> reasoning that some local models emit inline."""
    return _REASONING_BLOCK.sub("", text or "").strip()


class BaseLLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = 0.1, max_tokens: int = 4000) -> str:
        pass

    @abstractmethod
    def test_connection(self) -> dict:
        pass


class MockLLMProvider(BaseLLMProvider):
    name = "mock"

    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = 0.1, max_tokens: int = 4000) -> str:
        return "[Mock Mode — using deterministic template rendering]"

    def test_connection(self) -> dict:
        return {"status": "ok", "provider": "mock", "message": "Mock provider always available"}


class OpenAIProvider(BaseLLMProvider):
    name = "openai"

    def __init__(self, cfg: dict):
        self.model = cfg.get("model", "gpt-4")
        self.api_key = os.environ.get(cfg.get("api_key_env", "OPENAI_API_KEY"), "")
        self._temp = cfg.get("temperature", 0.1)
        self._max = cfg.get("max_tokens", 4000)

    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = None, max_tokens: int = None) -> str:
        import openai
        client = openai.OpenAI(api_key=self.api_key)
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": prompt})
        r = client.chat.completions.create(
            model=self.model, messages=msgs,
            temperature=temperature or self._temp,
            max_tokens=max_tokens or self._max,
        )
        return r.choices[0].message.content

    def test_connection(self) -> dict:
        try:
            import openai
            openai.OpenAI(api_key=self.api_key).models.list()
            return {"status": "ok", "provider": "openai", "model": self.model}
        except Exception as e:
            return {"status": "error", "provider": "openai", "message": str(e)}


class AnthropicProvider(BaseLLMProvider):
    name = "anthropic"

    def __init__(self, cfg: dict):
        self.model = cfg.get("model", "claude-sonnet-4-20250514")
        self.api_key = os.environ.get(cfg.get("api_key_env", "ANTHROPIC_API_KEY"), "")
        self._temp = cfg.get("temperature", 0.1)
        self._max = cfg.get("max_tokens", 4000)

    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = None, max_tokens: int = None) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        r = client.messages.create(
            model=self.model,
            max_tokens=max_tokens or self._max,
            system=system_prompt or "You are a helpful assistant.",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature or self._temp,
        )
        return r.content[0].text

    def test_connection(self) -> dict:
        if not self.api_key:
            return {"status": "error", "provider": "anthropic", "message": "API key not set"}
        return {"status": "ok", "provider": "anthropic", "model": self.model}


class AzureOpenAIProvider(BaseLLMProvider):
    name = "azure_openai"

    def __init__(self, cfg: dict):
        self.deployment = cfg.get("deployment", "gpt-4")
        self.api_key = os.environ.get(cfg.get("api_key_env", "AZURE_OPENAI_API_KEY"), "")
        self.endpoint = os.environ.get(cfg.get("endpoint_env", "AZURE_OPENAI_ENDPOINT"), "")
        self.api_version = cfg.get("api_version", "2024-02-15-preview")
        self._temp = cfg.get("temperature", 0.1)
        self._max = cfg.get("max_tokens", 4000)

    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = None, max_tokens: int = None) -> str:
        import openai
        client = openai.AzureOpenAI(
            api_key=self.api_key, azure_endpoint=self.endpoint,
            api_version=self.api_version,
        )
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": prompt})
        r = client.chat.completions.create(
            model=self.deployment, messages=msgs,
            temperature=temperature or self._temp,
            max_tokens=max_tokens or self._max,
        )
        return r.choices[0].message.content

    def test_connection(self) -> dict:
        if not self.api_key or not self.endpoint:
            return {"status": "error", "provider": "azure_openai", "message": "Key or endpoint not set"}
        return {"status": "ok", "provider": "azure_openai", "deployment": self.deployment}


class VertexAIGeminiProvider(BaseLLMProvider):
    name = "vertex_ai_gemini"

    def __init__(self, cfg: dict):
        self.model_name = cfg.get("model", "gemini-2.0-flash")
        self.project = cfg.get("project") or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        self.location = cfg.get("location", "asia-south1")
        self.api_key = os.environ.get(cfg.get("api_key_env", "GOOGLE_API_KEY"), "")
        self._temp = cfg.get("temperature", 0.15)
        self._max = cfg.get("max_tokens", 4000)

    def _client(self):
        from google import genai
        if self.api_key:
            return genai.Client(api_key=self.api_key)
        return genai.Client(vertexai=True, project=self.project, location=self.location)

    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = None, max_tokens: int = None) -> str:
        from google.genai import types
        client = self._client()
        config = types.GenerateContentConfig(
            system_instruction=system_prompt or None,
            temperature=temperature or self._temp,
            max_output_tokens=max_tokens or self._max,
        )
        response = client.models.generate_content(
            model=self.model_name, contents=prompt, config=config,
        )
        return response.text

    def test_connection(self) -> dict:
        try:
            client = self._client()
            from google.genai import types
            config = types.GenerateContentConfig(max_output_tokens=20)
            resp = client.models.generate_content(
                model=self.model_name, contents="Say hello", config=config,
            )
            mode = "api_key" if self.api_key else "vertex_ai"
            return {"status": "ok", "provider": "vertex_ai_gemini",
                    "model": self.model_name, "mode": mode, "response": resp.text[:50]}
        except Exception as e:
            raise RuntimeError(f"LLM connection failed: {e}. Provider: vertex_ai_gemini")


class OllamaProvider(BaseLLMProvider):
    name = "ollama"

    def __init__(self, cfg: dict):
        self.model = cfg.get("model", "llama3")
        # OLLAMA_HOST env var (set in Docker compose) takes priority over config
        self.base_url = os.environ.get("OLLAMA_HOST") or cfg.get("base_url", "http://localhost:11434")
        self._temp = cfg.get("temperature", 0.1)
        self._max = cfg.get("max_tokens", 4000)
        self._num_ctx = int(cfg.get("num_ctx", 8192))
        self._max_ctx = int(cfg.get("max_num_ctx", 32768))
        self._timeout = float(cfg.get("timeout_seconds", 600))
        # Reasoning models (qwen3, deepseek-r1): False skips the hidden "thinking" pass.
        self._think = cfg.get("think")

    def context_window(self, prompt: str, num_predict: int) -> int:
        """Smallest context bucket that holds the prompt plus the answer.

        Ollama silently drops the *start* of a prompt that exceeds ``num_ctx``,
        which would cut the system prompt and section instructions. Sizes step
        in doublings so Ollama reloads the model rarely (a reload happens
        whenever ``num_ctx`` changes).
        """
        estimated_tokens = len(prompt) // 3 + num_predict  # JSON-heavy text ≈ 3 chars/token
        window = self._num_ctx
        while window < estimated_tokens and window < self._max_ctx:
            window *= 2
        window = min(window, self._max_ctx)
        if estimated_tokens > window:
            log.warning("Prompt (~%d tokens incl. answer) exceeds max_num_ctx=%d; the start will be truncated",
                        estimated_tokens, window)
        return window

    def generate(self, prompt: str, system_prompt: str = "",
                 temperature: float = None, max_tokens: int = None) -> str:
        import httpx
        full = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        num_predict = self._max if max_tokens is None else max_tokens
        payload = {"model": self.model, "prompt": full, "stream": False,
                   "options": {"temperature": self._temp if temperature is None else temperature,
                               "num_predict": num_predict,
                               "num_ctx": self.context_window(full, num_predict)}}
        if self._think is not None:
            payload["think"] = bool(self._think)
        r = httpx.post(f"{self.base_url}/api/generate", json=payload, timeout=self._timeout)
        if r.status_code == 404:
            raise RuntimeError(f"Ollama model '{self.model}' is not installed. Run: ollama pull {self.model}")
        r.raise_for_status()
        return strip_reasoning(r.json().get("response", ""))

    def test_connection(self) -> dict:
        """Ollama is reachable and the configured model is installed."""
        try:
            import httpx
            r = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            models = [m["name"] for m in r.json().get("models", [])]
        except Exception as e:
            return {"status": "error", "provider": "ollama", "message": f"Ollama not reachable: {e}"}
        if self.model not in models and f"{self.model}:latest" not in models:
            return {"status": "error", "provider": "ollama", "models": models,
                    "message": f"Model '{self.model}' is not installed. Run: ollama pull {self.model}"}
        return {"status": "ok", "provider": "ollama", "model": self.model, "models": models}


# ─── Factory ────────────────────────────────────────────────────────────────

_PROVIDERS = {
    "mock": lambda c: MockLLMProvider(),
    "openai": lambda c: OpenAIProvider(c),
    "anthropic": lambda c: AnthropicProvider(c),
    "azure_openai": lambda c: AzureOpenAIProvider(c),
    "vertex_ai_gemini": lambda c: VertexAIGeminiProvider(c),
    "ollama": lambda c: OllamaProvider(c),
}


def create_llm_provider(provider_config: dict) -> BaseLLMProvider:
    ptype = provider_config.get("type")
    if not ptype:
        raise RuntimeError("LLM provider type not configured in llm_providers.yaml")
    factory = _PROVIDERS.get(ptype)
    if not factory:
        raise RuntimeError(f"Unknown LLM provider type: {ptype}")
    return factory(provider_config)
