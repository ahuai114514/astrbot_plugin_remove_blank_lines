from sanitizer import collapse_blank_lines


def test_whitespace_only_blank_lines():
    assert collapse_blank_lines("hello\n \n\t\nworld") == "hello\nworld"


def test_preserves_content_line_indentation():
    assert collapse_blank_lines("hello\n\n  world") == "hello\n  world"


def test_respects_configured_limit():
    assert collapse_blank_lines("a\n \n\n\n b", 2) == "a\n\n b"


def test_normalizes_line_endings():
    assert collapse_blank_lines("a\r\n \r\n\r\nb") == "a\nb"


def test_zero_removes_newlines():
    assert collapse_blank_lines("a\n \nb", 0) == "a b"
