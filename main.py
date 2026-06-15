from __future__ import annotations

from typing import Any

from astrbot.api import AstrBotConfig
from astrbot.api.event import AstrMessageEvent, filter
import astrbot.api.message_components as Comp
from astrbot.api.star import Context, Star, register

from .sanitizer import DEFAULT_MAX_CONSECUTIVE_NEWLINES, collapse_blank_lines

PLUGIN_ID = "astrbot_plugin_remove_blank_lines"


@register(PLUGIN_ID, "Codex", "自动删除机器人回复中的空行", "1.0.0")
class RemoveBlankLinesPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig | None = None):
        super().__init__(context)
        self.config = config

    @filter.on_decorating_result(priority=-100)
    async def remove_blank_lines(self, event: AstrMessageEvent) -> None:
        result = event.get_result()
        if result is None or not getattr(result, "chain", None):
            return

        max_newlines = self._config_get("max_consecutive_newlines", DEFAULT_MAX_CONSECUTIVE_NEWLINES)
        for component in result.chain:
            if isinstance(component, Comp.Plain):
                component.text = collapse_blank_lines(component.text, max_newlines)

    def _config_get(self, key: str, default: Any) -> Any:
        if self.config is None:
            return default
        if hasattr(self.config, "get"):
            return self.config.get(key, default)
        return getattr(self.config, key, default)
