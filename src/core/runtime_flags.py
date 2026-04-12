from __future__ import annotations

import os


def _flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def optional_mock_data_enabled() -> bool:
    return _flag("CAM_ENABLE_OPTIONAL_MOCK_DATA", default=False)
