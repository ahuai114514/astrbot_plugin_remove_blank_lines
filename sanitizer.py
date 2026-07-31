from __future__ import annotations

import re


DEFAULT_MAX_CONSECUTIVE_NEWLINES = 1


def collapse_blank_lines(text: str, max_consecutive_newlines: int = DEFAULT_MAX_CONSECUTIVE_NEWLINES) -> str:
    """Collapse repeated blank lines while preserving content-line whitespace."""
    limit = max(int(max_consecutive_newlines), 0)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if limit == 0:
        return re.sub(r"\n+", "", normalized)

    # The whitespace belongs to blank lines only; do not consume indentation
    # on the content line following the final newline.
    pattern = r"\n(?:[ \t]*\n){" + str(limit) + r",}"
    return re.sub(pattern, "\n" * limit, normalized)
