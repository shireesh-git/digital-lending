"""Ollama provider: context sizing and reasoning-text cleanup (no network)."""

from src.core.llm_provider import OllamaProvider, strip_reasoning


def _provider(**cfg):
    return OllamaProvider({"model": "qwen3:8b", "num_ctx": 8192, "max_num_ctx": 32768, **cfg})


def test_short_prompt_keeps_configured_window():
    assert _provider().context_window("x" * 3000, num_predict=2500) == 8192


def test_long_prompt_grows_window_in_doublings():
    # ~15,000 prompt tokens + 2,500 answer tokens needs the 32K bucket.
    assert _provider().context_window("x" * 45_000, num_predict=2500) == 32768
    assert _provider().context_window("x" * 24_000, num_predict=2500) == 16384


def test_window_is_capped_at_max():
    assert _provider().context_window("x" * 300_000, num_predict=2500) == 32768


def test_strip_reasoning():
    assert strip_reasoning("<think>plan\nsteps</think>\n## Section") == "## Section"
    assert strip_reasoning(None) == ""
