from __future__ import annotations

import re


DEFAULT_MAX_CONSECUTIVE_NEWLINES = 1


def collapse_blank_lines(text: str, max_consecutive_newlines: int = DEFAULT_MAX_CONSECUTIVE_NEWLINES) -> str:
    """Collapse repeated newlines while keeping up to the configured limit."""
    limit = max(int(max_consecutive_newlines), 0)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n{" + str(limit + 1) + r",}", "\n" * limit, normalized)
