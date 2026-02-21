from __future__ import annotations

from fast_diff_match_patch import diff as fast_diff


def text_changed(before: str, after: str) -> bool:
    chunks = fast_diff(before, after)
    return any(op in ("-", "+") for op, _count in chunks)

