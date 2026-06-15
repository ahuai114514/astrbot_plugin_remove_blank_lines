from sanitizer import collapse_blank_lines


def test_collapse_default_removes_blank_line():
    assert collapse_blank_lines("没关系的，博士\n\n我刚刚还以为") == "没关系的，博士\n我刚刚还以为"


def test_collapse_handles_windows_newlines():
    assert collapse_blank_lines("a\r\n\r\nb") == "a\nb"


def test_collapse_can_keep_one_blank_line():
    assert collapse_blank_lines("a\n\n\nb", 2) == "a\n\nb"
