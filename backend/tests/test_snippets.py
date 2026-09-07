from app.modules.memo.snippets import extract_snippets


def test_cjk_truncation_by_character() -> None:
    """中日文无空格分割，直接按字符截断并加上省略号。"""
    body = "长长前置文字，中文分词技术非常重要，后面跟着长长长长说明文字。"
    snippets = extract_snippets(body, "中文分词", context_chars=6)
    assert len(snippets) == 1
    snippet = snippets[0]
    assert "中文分词" in snippet
    assert snippet.startswith("...")
    assert snippet.endswith("...")


def test_japanese_truncation_by_character() -> None:
    body = "昨日の深刻なバグ修正対応について、明日までに対応します。"
    snippets = extract_snippets(body, "バグ修正", context_chars=5)
    assert len(snippets) == 1
    assert "バグ修正" in snippets[0]
    assert "深刻なバグ修正対応に" in snippets[0]


def test_english_word_boundary_avoid_chopping_words() -> None:
    """英文词边界：避免把单词切成半截（例如 remember 切成 rem...）。"""
    body = (
        "Please remember that we must invalidate the authentication "
        "token immediately after logout."
    )
    snippets = extract_snippets(body, "token", context_chars=12)
    assert len(snippets) == 1
    snippet = snippets[0]
    assert "token" in snippet
    words = snippet.replace("...", "").split()
    assert "token" in words
    for w in words:
        assert w in [
            "Please",
            "remember",
            "that",
            "we",
            "must",
            "invalidate",
            "the",
            "authentication",
            "token",
            "immediately",
            "after",
            "logout.",
        ]


def test_multiple_matches_in_one_body_distant_produces_multiple_snippets() -> None:
    """一条正文多处命中（距离远）时生成多个独立片段。"""
    paragraph = "A paragraph explaining unrelated operational details...\n"
    body = (
        "Part 1: The database connection failed with timeout error.\n"
        + paragraph * 3
        + "Part 2: Later we found another database connection leak in the worker pool."
    )
    snippets = extract_snippets(body, "database connection", context_chars=15)
    assert len(snippets) == 2
    assert "failed with timeout" in snippets[0] and "database connection" in snippets[0]
    assert "leak in the worker" in snippets[1]
    assert "database connection" in snippets[1]


def test_multiple_matches_in_one_body_close_merges_into_one_snippet() -> None:
    """一条正文多处命中（距离近）时合并为一个连续片段。"""
    body = "The token is generated, and then this token is verified."
    snippets = extract_snippets(body, "token", context_chars=10)
    assert len(snippets) == 1
    assert "The token is generated, and then this token is verified." in snippets[0]


def test_match_at_very_beginning_of_body() -> None:
    """命中位于正文开头：左侧无省略号。"""
    body = "Authentication starts here and continues down to the rest of the flow..."
    snippets = extract_snippets(body, "Authentication", context_chars=15)
    assert len(snippets) == 1
    assert not snippets[0].startswith("...")
    assert snippets[0].startswith("Authentication starts here")
    assert snippets[0].endswith("...")


def test_match_at_very_end_of_body() -> None:
    """命中位于正文结尾：右侧无省略号。"""
    body = "All system resources have been released and the process ended with success."
    snippets = extract_snippets(body, "success", context_chars=15)
    assert len(snippets) == 1
    assert snippets[0].startswith("...")
    assert snippets[0].endswith("success.")
    assert not snippets[0].endswith("...")


def test_keyword_crosses_truncation_boundary_keyword_is_never_cut() -> None:
    """关键词横跨截断边界：无论上下文多短，关键词本身始终完整保留。"""
    long_keyword = "VERY_LONG_UNINTERRUPTED_IDENTIFIER_THAT_EXCEEDS_CONTEXT_LENGTH"
    body = f"prefix content before {long_keyword} suffix content after"
    # Even with context_chars=3, the full keyword must remain intact
    snippets = extract_snippets(body, long_keyword, context_chars=3)
    assert len(snippets) == 1
    assert long_keyword in snippets[0]
    assert snippets[0].startswith("...")
    assert snippets[0].endswith("...")


def test_case_insensitive_matching() -> None:
    body = "We encountered a Severe Bug in production."
    snippets = extract_snippets(body, "bug", context_chars=10)
    assert len(snippets) == 1
    assert "Severe Bug in production." in snippets[0]


def test_empty_or_whitespace_query_or_body() -> None:
    assert extract_snippets("", "keyword") == []
    assert extract_snippets("body", "") == []
    assert extract_snippets("body", "   ") == []
    assert extract_snippets("body", "notfound") == []
