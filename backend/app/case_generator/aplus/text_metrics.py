"""Word-count guards aligned to P2/P3 prompts."""

from __future__ import annotations


def word_count(text: str) -> int:
    return len(text.split())


def letter_words_ok(text: str) -> bool:
    n = word_count(text)
    return 200 <= n <= 500


def context_words_ok(text: str) -> bool:
    n = word_count(text)
    return 80 <= n <= 250
