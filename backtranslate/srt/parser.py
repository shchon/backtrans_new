import logging
import re


logger = logging.getLogger(__name__)


def _timestamp_to_ms(ts):
    h, m, s_ms = ts.split(":")
    s, ms = s_ms.split(",")
    return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)


def _strip_tags(text):
    return re.sub(r"<[^>]+>", "", text)


def parse_srt(content):
    """Parse SRT content into list of dicts with keys: index, start, end, text."""
    # Handle BOM (byte order mark) that some text editors add
    if content.startswith("﻿"):
        content = content[1:]
    content = content.replace("\r\n", "\n")

    if not content.strip():
        return []

    blocks = [b.strip() for b in content.strip().split("\n\n") if b.strip()]
    result = []

    pattern = re.compile(
        r"^(\d+)\s*\n"
        r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n"
        r"([\s\S]+)$",
        re.MULTILINE,
    )

    for block in blocks:
        m = pattern.match(block)
        if not m:
            logger.warning("Skipping malformed SRT block: %s", block[:80])
            continue
        idx_str, start_ts, end_ts, text = m.groups()
        result.append({
            "index": int(idx_str),
            "start": _timestamp_to_ms(start_ts),
            "end": _timestamp_to_ms(end_ts),
            "text": _strip_tags(text.strip()),
        })

    return result
