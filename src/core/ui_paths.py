"""Location of the bundled single-page UI, and assembly of its HTML shell."""

import re
from pathlib import Path

UI_ROOT = Path(__file__).resolve().parents[1] / "ui"
TEMPLATES_ROOT = UI_ROOT / "templates"

# A line holding only <!-- include: pages/summary.html --> is replaced by that file.
# Each page lives in its own file (templates/pages/) so the shell stays short.
_INCLUDE = re.compile(r"^[ \t]*<!-- include: ([\w./-]+\.html) -->[ \t]*$", re.MULTILINE)


def render_spa() -> str:
    """index.html with its page includes inlined (read on every request, so edits show on refresh)."""
    root = TEMPLATES_ROOT.resolve()

    def include(match: re.Match) -> str:
        path = (root / match.group(1)).resolve()
        if root not in path.parents:
            raise ValueError(f"UI include outside the templates folder: {match.group(1)}")
        return path.read_text(encoding="utf-8-sig").rstrip("\n")

    shell = (root / "index.html").read_text(encoding="utf-8").lstrip("﻿")  # a stray BOM forces quirks mode
    return _INCLUDE.sub(include, shell)
