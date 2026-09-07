from typing import NamedTuple


class MatchSpan(NamedTuple):
    start: int
    end: int


def _is_word_char(char: str) -> bool:
    """ASCII alphanumeric or underscore, forming English words."""
    return char.isascii() and (char.isalnum() or char == "_")


def _adjust_left_boundary(body: str, left: int, match_start: int) -> int:
    """Where to start the snippet: `left`, backed up to a word boundary.

    English is cut between words, so "rem|ember" becomes "remember"; CJK runs
    have no such boundary and are cut where they are. The result is clamped to
    `match_start`, so widening the snippet can never swallow the keyword.
    """
    if left <= 0:
        return 0

    if _is_word_char(body[left - 1]) and _is_word_char(body[left]):
        pos = left
        while pos > 0 and _is_word_char(body[pos - 1]):
            pos -= 1
        return min(pos, match_start)

    return min(left, match_start)


def _adjust_right_boundary(body: str, right: int, match_end: int) -> int:
    """Where to end the snippet: `right`, run on to a word boundary.

    The mirror of `_adjust_left_boundary`: "token|izer" becomes "tokenizer",
    and the result is clamped to `match_end` so the keyword survives whole.
    """
    if right >= len(body):
        return len(body)

    if _is_word_char(body[right - 1]) and _is_word_char(body[right]):
        pos = right
        while pos < len(body) and _is_word_char(body[pos]):
            pos += 1
        return max(pos, match_end)

    return max(right, match_end)


def extract_snippets(
    body: str,
    query: str,
    context_chars: int = 25,
    max_snippets: int = 5,
) -> tuple[list[str], int]:
    """The pieces of `body` worth showing for `query`, and how many there are.

    Returns at most `max_snippets` of them alongside the total, so a memo that
    matches nine times can say so rather than quietly showing five — seeing
    only the first hit is how you misjudge whether a memo is the one you want
    (spec 搜索 29).

    Pure: no database, no filesystem. Keywords survive whole, English is cut
    between words and CJK between characters, neighbouring hits merge into one
    piece, and the ellipsis is dropped where the body itself begins or ends.
    """
    q = query.strip()
    if not q or not body:
        return [], 0

    body_lower = body.lower()
    q_lower = q.lower()

    # 1. Find all match locations
    matches: list[MatchSpan] = []
    start_search = 0
    while True:
        pos = body_lower.find(q_lower, start_search)
        if pos == -1:
            break
        matches.append(MatchSpan(pos, pos + len(q)))
        start_search = pos + max(1, len(q))

    if not matches:
        return [], 0

    # 2. Build and merge windows
    windows: list[list[int]] = []
    for m in matches:
        raw_left = max(0, m.start - context_chars)
        raw_right = min(len(body), m.end + context_chars)
        windows.append([raw_left, raw_right, m.start, m.end])

    # Merge nearby windows if gap <= context_chars * 2
    merge_gap_threshold = max(20, context_chars * 2)
    merged: list[list[int]] = []
    for w in windows:
        if not merged:
            merged.append(w)
            continue
        prev = merged[-1]
        if w[0] <= prev[1] + merge_gap_threshold:
            prev[1] = max(prev[1], w[1])
            prev[3] = max(prev[3], w[3])
        else:
            merged.append(w)

    # 3. Adjust boundaries for each merged snippet
    snippets: list[str] = []
    for w in merged[:max_snippets]:
        raw_left, raw_right, first_match_start, last_match_end = w
        final_left = _adjust_left_boundary(body, raw_left, first_match_start)
        final_right = _adjust_right_boundary(body, raw_right, last_match_end)

        chunk = body[final_left:final_right]
        cleaned = " ".join(chunk.split())

        prefix = "..." if final_left > 0 else ""
        suffix = "..." if final_right < len(body) else ""
        snippets.append(f"{prefix}{cleaned}{suffix}")

    return snippets, len(merged)
