from __future__ import annotations

import ast
import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class Plain:
    def __init__(self, text: str):
        self.text = text


class StubStar:
    def __init__(self, context):
        self.context = context


def load_plugin():
    """Load the plugin against in-memory API stubs without importing AstrBot.

    Returns:
        The plugin class with its event decorator metadata preserved.
    """

    def decorator(event_name):
        def factory(**kwargs):
            def decorate(function):
                function.hook_event = event_name
                return function

            return decorate

        return factory

    modules = {
        name: types.ModuleType(name)
        for name in (
            "astrbot",
            "astrbot.api",
            "astrbot.api.event",
            "astrbot.api.message_components",
            "astrbot.api.star",
            "_blank_lines_tests",
        )
    }
    modules["astrbot.api"].AstrBotConfig = dict
    modules["astrbot.api.event"].AstrMessageEvent = object
    modules["astrbot.api.event"].filter = SimpleNamespace(
        on_decorating_result=decorator("decorate"),
        on_using_llm_tool=decorator("tool_start"),
    )
    modules["astrbot.api.message_components"].Plain = Plain
    modules["astrbot.api.star"].Context = object
    modules["astrbot.api.star"].Star = StubStar
    modules["astrbot.api.star"].register = lambda *args, **kwargs: lambda cls: cls
    modules["_blank_lines_tests"].__path__ = [str(Path(__file__).parent)]
    with patch.dict(sys.modules, modules):
        spec = importlib.util.spec_from_file_location(
            "_blank_lines_tests.main", Path(__file__).with_name("main.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module.RemoveBlankLinesPlugin


def make_event(message: str = "", result=None):
    """Build a message event that records tool-send duplicate suppression data.

    Args:
        message: Incoming message text used by plugin exclusion rules.
        result: Optional ordinary reply result.

    Returns:
        A minimal event and its extra-data dictionary.
    """
    extras = {}
    return SimpleNamespace(
        unified_msg_origin="test:FriendMessage:user",
        message_str=message,
        message_obj=None,
        get_result=lambda: result,
        get_extra=lambda key, default=None: extras.get(key, default),
        set_extra=extras.__setitem__,
    ), extras


def load_core_method(path: Path, class_name: str, method_name: str, namespace):
    """Compile one deployed core method without executing package imports.

    Args:
        path: Core source file to inspect.
        class_name: Class declaring the method.
        method_name: Method to compile.
        namespace: Explicit in-memory dependencies for the method.

    Returns:
        The compiled method function.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    method = next(
        node
        for node in cls.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == method_name
    )
    future = ast.ImportFrom(
        module="__future__", names=[ast.alias(name="annotations")], level=0
    )
    isolated = ast.fix_missing_locations(
        ast.Module(body=[future, method], type_ignores=[])
    )
    exec(compile(isolated, str(path), "exec"), namespace)
    return namespace[method_name]


class ToolMessageTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.plugin_class = load_plugin()

    async def test_plain_components_only_and_session_preserved(self):
        plugin = self.plugin_class(None, {})
        event, _ = make_event()
        messages = [
            {"type": "PLAIN", "text": "first\n \nsecond"},
            {
                "type": "file",
                "text": "file\n\nname.txt",
                "url": "https://example.invalid/file",
            },
            {"type": "image", "url": "https://example.invalid/image"},
        ]
        args = {"messages": messages, "session": "other:FriendMessage:target"}
        await plugin.remove_tool_message_blank_lines(
            event, SimpleNamespace(name="send_message_to_user"), args
        )
        self.assertEqual(messages[0]["text"], "first\nsecond")
        self.assertEqual(messages[1]["text"], "file\n\nname.txt")
        self.assertEqual(messages[2]["url"], "https://example.invalid/image")
        self.assertEqual(args["session"], "other:FriendMessage:target")

    async def test_other_tools_are_unchanged(self):
        plugin = self.plugin_class(None, {})
        event, _ = make_event()
        args = {"messages": [{"type": "plain", "text": "a\n\nb"}]}
        await plugin.remove_tool_message_blank_lines(
            event, SimpleNamespace(name="other_tool"), args
        )
        self.assertEqual(args["messages"][0]["text"], "a\n\nb")

    async def test_configured_newline_limits(self):
        event, _ = make_event()
        for limit, expected in ((0, "ab"), (1, "a\nb"), (2, "a\n\nb")):
            with self.subTest(limit=limit):
                plugin = self.plugin_class(None, {"max_consecutive_newlines": limit})
                args = {"messages": [{"type": "plain", "text": "a\n\n\nb"}]}
                await plugin.remove_tool_message_blank_lines(
                    event, SimpleNamespace(name="send_message_to_user"), args
                )
                self.assertEqual(args["messages"][0]["text"], expected)

    async def test_blacklist_and_global_mode_rules(self):
        event, _ = make_event("astrbot_plugin_example output")
        for config in (
            {"plugin_blacklist": ["astrbot_plugin_example"]},
            {"apply_to_llm_output_globally": False},
        ):
            with self.subTest(config=config):
                plugin = self.plugin_class(None, config)
                args = {"messages": [{"type": "plain", "text": "a\n\nb"}]}
                await plugin.remove_tool_message_blank_lines(
                    event, SimpleNamespace(name="send_message_to_user"), args
                )
                self.assertEqual(args["messages"][0]["text"], "a\n\nb")

    async def test_malformed_arguments_preserve_tool_validation(self):
        plugin = self.plugin_class(None, {})
        event, _ = make_event()
        for args in (
            None,
            {},
            {"messages": None},
            {"messages": "invalid"},
            {"messages": [None, 42, {}, {"type": "plain", "text": None}]},
        ):
            with self.subTest(args=args):
                await plugin.remove_tool_message_blank_lines(
                    event, SimpleNamespace(name="send_message_to_user"), args
                )

    async def test_ordinary_reply_still_processed(self):
        text = Plain("first\n\nsecond")
        event, _ = make_event(result=SimpleNamespace(chain=[text]))
        await self.plugin_class(None, {}).remove_blank_lines(event)
        self.assertEqual(text.text, "first\nsecond")

    async def test_deployed_agent_hook_to_send_tool_without_network(self):
        root = Path(os.environ.get("ASTRBOT_SOURCE_ROOT", "/AstrBot"))
        if not (root / "astrbot/core/tools/message_tools.py").is_file():
            self.skipTest("Set ASTRBOT_SOURCE_ROOT to exercise deployed core methods")
        plugin = self.plugin_class(None, {})
        event, extras = make_event()
        tool = SimpleNamespace(name="send_message_to_user")
        captured = []

        async def dispatch_hook(actual_event, event_type, actual_tool, args):
            self.assertEqual(event_type, "tool_start")
            for name in dir(plugin):
                handler = getattr(plugin, name)
                if getattr(handler, "hook_event", None) == event_type:
                    await handler(actual_event, actual_tool, args)

        async def capture_send(session, chain):
            captured.append(chain)
            return True

        class MessageChain:
            def __init__(self, chain):
                self.chain = chain

            def get_plain_text(self):
                return "".join(
                    item.text for item in self.chain if isinstance(item, Plain)
                )

        class Session:
            @classmethod
            def from_str(cls, value):
                return value

        wrapper = SimpleNamespace(
            context=SimpleNamespace(
                event=event, context=SimpleNamespace(send_message=capture_send)
            )
        )
        on_start = load_core_method(
            root / "astrbot/core/astr_agent_hooks.py",
            "MainAgentHooks",
            "on_tool_start",
            {
                "call_event_hook": dispatch_hook,
                "EventType": SimpleNamespace(OnUsingLLMToolEvent="tool_start"),
            },
        )
        call = load_core_method(
            root / "astrbot/core/tools/message_tools.py",
            "SendMessageToUserTool",
            "call",
            {
                "Comp": SimpleNamespace(Plain=Plain),
                "MessageChain": MessageChain,
                "MessageSession": Session,
            },
        )
        args = {"messages": [{"type": "plain", "text": "first\n \nsecond"}]}
        await on_start(None, wrapper, tool, args)
        result = await call(None, wrapper, **args)
        self.assertTrue(result.startswith("Message sent"))
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0].chain[0].text, "first\nsecond")
        self.assertEqual(
            extras["_send_message_to_user_current_session_plain_texts"],
            ["first\nsecond"],
        )


if __name__ == "__main__":
    unittest.main()
