from typing import NamedTuple


class MatchSpan(NamedTuple):
    start: int
    end: int


def _is_word_char(char: str) -> bool:
    """ASCII alphanumeric or underscore, forming English words."""
    return char.isascii() and (char.isalnum() or char == "_")


def _adjust_left_boundary(body: str, left: int, match_start: int) -> int:
    """Adjust left boundary to respect English word boundaries, while preserving

    CJK characters by slicing directly at character positions.
    Always stays <= match_start.
    """
    if left <= 0:
        return 0

    # If cutting right inside an English word (e.g. "rem|ember")
    if _is_word_char(body[left - 1]) and _is_word_char(body[left]):
        # Move outward (leftward) to the start of the word
        pos = left
        while pos > 0 and _is_word_char(body[pos - 1]):
            pos -= 1
        return pos

    return left


def _adjust_right_boundary(body: str, right: int, match_end: int) -> int:
    """Adjust right boundary to respect English word boundaries.

    Always stays >= match_end.
    """
    if right >= len(body):
        return len(body)

    # If cutting right inside an English word (e.g. "token|izer")
    if _is_word_char(body[right - 1]) and _is_word_char(body[right]):
        # Move outward (rightward) to complete the word
        pos = right
        while pos < len(body) and _is_word_char(body[pos]):
            pos += 1
        return pos

    return right


def extract_snippets(
    body: str,
    query: str,
    context_chars: int = 25,
    max_snippets: int = 5,
) -> list[str]:
    """Pure function extracting contextual snippets for query hits in body.

    Zero I/O, no DB or filesystem access.
    - Preserves keyword entirely across boundaries (never truncates the matched term).
    - Truncates English on word boundaries, CJK on characters.
    - Merges nearby matches into one snippet,
      outputs separate snippets for distant hits.
    - Omits leading/trailing ellipsis if match touches start/end of body.
    """
    q = query.strip()
    if not q or not body:
        return []

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
        return []

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

    return snippets
