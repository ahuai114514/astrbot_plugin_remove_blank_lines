"""Tests for collapse_blank_lines sanitizer."""
from __future__ import annotations

import pytest

from sanitizer import collapse_blank_lines


class TestBasicCollapse:
    """Basic newline collapsing."""

    def test_no_change_single_newline(self):
        assert collapse_blank_lines("hello\nworld") == "hello\nworld"

    def test_double_newline_to_single(self):
        assert collapse_blank_lines("hello\n\nworld") == "hello\nworld"

    def test_triple_newline_to_single(self):
        assert collapse_blank_lines("hello\n\n\nworld") == "hello\nworld"

    def test_empty_string(self):
        assert collapse_blank_lines("") == ""

    def test_no_newline(self):
        assert collapse_blank_lines("hello world") == "hello world"


class TestWhitespaceBlankLines:
    """Blank lines containing whitespace — the main bug being fixed."""

    def test_space_only_blank_line(self):
        assert collapse_blank_lines("hello\n \nworld") == "hello\nworld"

    def test_tab_only_blank_line(self):
        assert collapse_blank_lines("hello\n\t\nworld") == "hello\nworld"

    def test_multiple_spaces_blank_line(self):
        assert collapse_blank_lines("hello\n   \nworld") == "hello\nworld"

    def test_mixed_whitespace_blank_line(self):
        assert collapse_blank_lines("hello\n \t \nworld") == "hello\nworld"

    def test_multiple_whitespace_blank_lines(self):
        assert collapse_blank_lines("hello\n \n \nworld") == "hello\nworld"

    def test_whitespace_and_pure_blank_mix(self):
        assert collapse_blank_lines("hello\n\n \n\nworld") == "hello\nworld"


class TestLineEndingNormalization:
    """CRLF and CR should be normalized to LF before processing."""

    def test_crlf_normalization(self):
        assert collapse_blank_lines("hello\r\n\r\nworld") == "hello\nworld"

    def test_cr_normalization(self):
        assert collapse_blank_lines("hello\r\rworld") == "hello\nworld"

    def test_mixed_endings(self):
        assert collapse_blank_lines("hello\r\n\r \r\nworld") == "hello\nworld"


class TestMaxConsecutiveNewlines:
    """Configurable max_consecutive_newlines."""

    def test_limit_2_keeps_one_blank_line(self):
        result = collapse_blank_lines("hello\n\n\nworld", max_consecutive_newlines=2)
        assert result == "hello\n\nworld"

    def test_limit_2_with_whitespace(self):
        result = collapse_blank_lines("hello\n \n \n \nworld", max_consecutive_newlines=2)
        assert result == "hello\n\nworld"

    def test_limit_0_removes_all_newlines(self):
        result = collapse_blank_lines("hello\n\nworld", max_consecutive_newlines=0)
        assert result == "helloworld"

    def test_limit_0_with_whitespace(self):
        result = collapse_blank_lines("hello\n \nworld", max_consecutive_newlines=0)
        assert result == "helloworld"


class TestEdgeCases:
    """Edge cases."""

    def test_leading_blank_lines(self):
        assert collapse_blank_lines("\n\nhello") == "\nhello"

    def test_trailing_blank_lines(self):
        assert collapse_blank_lines("hello\n\n") == "hello\n"

    def test_only_newlines(self):
        assert collapse_blank_lines("\n\n\n") == "\n"

    def test_only_whitespace_newlines(self):
        assert collapse_blank_lines("\n \n \n") == "\n"

    def test_preserve_trailing_whitespace_on_content_line(self):
        """Trailing spaces on non-blank lines should be preserved."""
        # "hello   \n\nworld" — the \n\n is collapsed, but "hello   " keeps its spaces
        result = collapse_blank_lines("hello   \n\nworld")
        assert result == "hello   \nworld"

    def test_multiple_paragraphs(self):
        text = "para1\n\npara2\n\npara3"
        result = collapse_blank_lines(text)
        assert result == "para1\npara2\npara3"

    def test_multiple_paragraphs_with_whitespace_blanks(self):
        text = "para1\n \npara2\n\t\npara3"
        result = collapse_blank_lines(text)
        assert result == "para1\npara2\npara3"
