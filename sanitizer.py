from __future__ import annotations

import re


DEFAULT_MAX_CONSECUTIVE_NEWLINES = 1


def collapse_blank_lines(text: str, max_consecutive_newlines: int = DEFAULT_MAX_CONSECUTIVE_NEWLINES) -> str:
    """Collapse repeated blank lines while keeping up to the configured limit.

    Handles lines that contain only whitespace (spaces, tabs) between newlines,
    which the original regex ``\\n{2,}`` missed entirely.
    """
    limit = max(int(max_consecutive_newlines), 0)
    # Normalize line endings first
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")

    if limit == 0:
        # Remove all newlines (merge into one line)
        return normalized.replace("\n", "")

    # Match 2+ newlines with optional whitespace between them:
    #   \n\n        → matched
    #   \n \n       → matched (space-only blank line)
    #   \n\t\n      → matched (tab-only blank line)
    #   \n   \n    → matched
    pattern = r"(?:\n[ \t]*){" + str(limit + 1) + r",}"
    return re.sub(pattern, "\n" * limit, normalized)
