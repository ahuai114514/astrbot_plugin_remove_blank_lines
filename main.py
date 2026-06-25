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

        if not self._should_process_event(event):
            return

        max_newlines = self._config_get("max_consecutive_newlines", DEFAULT_MAX_CONSECUTIVE_NEWLINES)
        for component in result.chain:
            if isinstance(component, Comp.Plain):
                component.text = collapse_blank_lines(component.text, max_newlines)

    def _should_process_event(self, event: AstrMessageEvent) -> bool:
        event_text = self._collect_event_metadata_text(event)
        if self._is_blacklisted(event_text):
            return False

        return self._is_global_mode_enabled() or not self._looks_like_plugin_output(event_text)

    def _is_global_mode_enabled(self) -> bool:
        return bool(self._config_get("apply_to_llm_output_globally", True))

    def _config_get(self, key: str, default: Any) -> Any:
        if self.config is None:
            return default
        if hasattr(self.config, "get"):
            return self.config.get(key, default)
        return getattr(self.config, key, default)

    def _normalized_plugin_ids(self, value: Any) -> set[str]:
        if not isinstance(value, (list, tuple)):
            return set()
        return {
            str(item).strip().lower()
            for item in value
            if isinstance(item, str) and item.strip()
        }

    def _is_blacklisted(self, event_text: str) -> bool:
        return self._matches_plugin_ids(
            event_text,
            self._config_get("plugin_blacklist", []),
        )

    def _looks_like_plugin_output(self, event_text: str) -> bool:
        return "astrbot_plugin_" in event_text

    def _matches_plugin_ids(self, event_text: str, value: Any) -> bool:
        plugin_ids = self._normalized_plugin_ids(value)
        return any(plugin_id in event_text for plugin_id in plugin_ids)

    def _collect_event_metadata_text(self, event: AstrMessageEvent) -> str:
        values: list[str] = []
        for attr in (
            "unified_msg_origin",
            "message_str",
        ):
            value = getattr(event, attr, None)
            if value:
                values.append(str(value))

        message_obj = getattr(event, "message_obj", None)
        if message_obj is not None:
            for attr in ("sender", "sub_type", "message_type", "raw_message"):
                value = getattr(message_obj, attr, None)
                if value:
                    values.append(str(value))

        result = event.get_result()
        if result is not None:
            for attr in ("__dict__",):
                value = getattr(result, attr, None)
                if value:
                    values.append(str(value))

        return "\n".join(values).lower()
