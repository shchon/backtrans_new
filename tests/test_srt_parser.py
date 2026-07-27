from backtranslate.srt.parser import parse_srt


def test_parse_simple_srt():
    content = """1
00:00:01,000 --> 00:00:03,000
你好

2
00:00:05,000 --> 00:00:08,000
再见
"""
    result = parse_srt(content)
    assert len(result) == 2
    assert result[0]["index"] == 1
    assert result[0]["start"] == 1000
    assert result[0]["end"] == 3000
    assert result[0]["text"] == "你好"
    assert result[1]["index"] == 2
    assert result[1]["text"] == "再见"


def test_parse_srt_with_milliseconds():
    content = """1
00:01:30,500 --> 00:01:35,200
测试字幕
"""
    result = parse_srt(content)
    assert result[0]["start"] == 90500
    assert result[0]["end"] == 95200


def test_parse_empty_srt():
    result = parse_srt("")
    assert result == []


def test_parse_srt_strips_html_tags_in_text():
    content = """1
00:00:01,000 --> 00:00:03,000
<i>斜体文字</i>
"""
    result = parse_srt(content)
    assert "<i>" not in result[0]["text"]


def test_parse_srt_with_windows_line_endings():
    content = "1\r\n00:00:01,000 --> 00:00:03,000\r\n你好\r\n"
    result = parse_srt(content)
    assert len(result) == 1
    assert result[0]["text"] == "你好"


def test_parse_srt_with_bom():
    content = "﻿1\n00:00:01,000 --> 00:00:03,000\n你好\n\n2\n00:00:04,000 --> 00:00:06,000\n再见\n"
    result = parse_srt(content)
    assert len(result) == 2
    assert result[0]["index"] == 1
    assert result[0]["text"] == "你好"
    assert result[1]["text"] == "再见"
