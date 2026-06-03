"""Word-count guards aligned to P2/P3 prompts."""

from __future__ import annotations

import re

LETTER_MIN_WORDS = 200
LETTER_MAX_WORDS = 500


def word_count(text: str) -> int:
    return len(text.split())


def letter_words_ok(text: str) -> bool:
    n = word_count(text)
    return LETTER_MIN_WORDS <= n <= LETTER_MAX_WORDS


def context_words_ok(text: str) -> bool:
    n = word_count(text)
    return 80 <= n <= 250


# Ordered trims — safe for upgraded letters; preserves flaws and appeal rights.
_LETTER_TRIMS: tuple[tuple[str, str], ...] = (
    (
        "under UnitedHealthcare Coverage Determination Guideline (CDG; authoritative "
        "clinical policy for this review)",
        "under UnitedHealthcare Coverage Determination Guideline (CDG)",
    ),
    (
        "under Cigna Medical Coverage Policy (CPG/MM_ series)",
        "under Cigna Medical Coverage Policy",
    ),
    (
        "Clinical policy applied (Clinical Policy Bulletin / CPB):",
        "Clinical policy applied:",
    ),
    (
        "Many members use this information when preparing an appeal. ",
        "",
    ),
    (
        "including plain-language descriptions, as required by applicable federal standards.",
        "as required by applicable federal standards.",
    ),
    (
        "This review was performed using clinical criteria applied through our "
        "designated utilization-management program. The specific criteria document is "
        "available upon request.\n\n",
        "",
    ),
    (
        "The requesting provider may submit additional records, but the current file "
        "does not support approval.\n\n",
        "",
    ),
    (
        " Additional plan language regarding experimental/investigational "
        "definitions, network status, and member cost-sharing may apply and "
        "is available upon request.",
        "",
    ),
    (
        " This determination is based solely on the information available at the time of review.",
        "",
    ),
    (
        "You may also have the right to receive, upon request and without charge, "
        "copies of documents relevant to this determination.",
        "",
    ),
)

_DUPE_PARA_RE = re.compile(
    r"(\n\nStandard criteria apply regardless of information previously sent to the plan\.)+",
    re.IGNORECASE,
)

_MHPAEA_ASYMMETRY_DUPE_RE = re.compile(
    r"(For behavioral health benefits,[^.]+\.)\s+For behavioral health benefits,[^.]+\.",
    re.IGNORECASE,
)

_P2P_SPLICE_RE = re.compile(
    r"If your provider wishes to discuss this determination\.\s*"
    r"(\n\nYour treating physician may request a peer-to-peer discussion.+?"
    r"authorization decision\.), they may contact our physician review line",
    re.DOTALL | re.IGNORECASE,
)

_P2P_SPLICE_INLINE_RE = re.compile(
    r"If your provider wishes to discuss this determination\.\s+"
    r"(Your treating physician may request a peer-to-peer discussion.+?"
    r"(?:authorization decision|appeal process)\.), they may contact our physician review line\.",
    re.DOTALL | re.IGNORECASE,
)

_P2P_SPLICE_APPEAL_COMMA_RE = re.compile(
    r"If your provider wishes to discuss this determination\.\s*"
    r"(\n\nYour treating physician may request a peer-to-peer discussion.+?"
    r"written appeal\.), they may contact our physician review line\.",
    re.DOTALL | re.IGNORECASE,
)

_P2P_SPLICE_APPEAL_COMMA_INLINE_RE = re.compile(
    r"If your provider wishes to discuss this determination\.\s+"
    r"(Your treating physician may request a peer-to-peer discussion.+?"
    r"written appeal\.), they may contact our physician review line\.",
    re.DOTALL | re.IGNORECASE,
)


def _reinsert_p2p_block(out: str, p2p: str) -> str:
    if "YOUR RIGHT TO INFORMATION" in out and p2p.lower() not in out.lower():
        return out.replace(
            "\n\nYOUR RIGHT TO INFORMATION",
            f"\n\n{p2p}\n\nYOUR RIGHT TO INFORMATION",
            1,
        )
    return out


def repair_denial_letter_artifacts(letter: str) -> str:
    """Fix known corruption from an earlier P2P splice into the provider-discussion sentence."""
    out = letter
    m = _P2P_SPLICE_RE.search(out)
    if m:
        p2p = m.group(1).strip()
        out = _P2P_SPLICE_RE.sub(
            "If your provider wishes to discuss this determination, they may contact "
            "our physician review line",
            out,
            count=1,
        )
        out = _reinsert_p2p_block(out, p2p)
    m_inline = _P2P_SPLICE_INLINE_RE.search(out)
    if m_inline:
        p2p = m_inline.group(1).strip()
        p2p = re.sub(r"process\.\s*$", "process.", p2p)
        out = _P2P_SPLICE_INLINE_RE.sub(
            "If your provider wishes to discuss this determination, they may contact "
            "our physician review line.",
            out,
            count=1,
        )
        out = _reinsert_p2p_block(out, p2p)
    m_appeal = _P2P_SPLICE_APPEAL_COMMA_RE.search(out)
    if m_appeal:
        p2p = m_appeal.group(1).strip()
        out = _P2P_SPLICE_APPEAL_COMMA_RE.sub(
            "If your provider wishes to discuss this determination, they may contact "
            "our physician review line.",
            out,
            count=1,
        )
        out = _reinsert_p2p_block(out, p2p)
    m_appeal_inline = _P2P_SPLICE_APPEAL_COMMA_INLINE_RE.search(out)
    if m_appeal_inline:
        p2p = m_appeal_inline.group(1).strip()
        out = _P2P_SPLICE_APPEAL_COMMA_INLINE_RE.sub(
            "If your provider wishes to discuss this determination, they may contact "
            "our physician review line.",
            out,
            count=1,
        )
        out = _reinsert_p2p_block(out, p2p)
    out = re.sub(r"determination\., they may", "determination, they may", out)
    out = re.sub(r"decision\., they may", "decision, they may", out)
    out = _MHPAEA_ASYMMETRY_DUPE_RE.sub(r"\1", out, count=1)
    return out


def _split_protected_letter_tail(letter: str) -> tuple[str, str]:
    """Keep appeal / information rights blocks intact when trimming word count."""
    markers = ("YOUR RIGHT TO INFORMATION", "APPEAL RIGHTS")
    idx = len(letter)
    for marker in markers:
        pos = letter.find(marker)
        if pos != -1 and pos < idx:
            idx = pos
    if idx < len(letter):
        return letter[:idx].rstrip(), "\n\n" + letter[idx:].lstrip()
    return letter, ""


def fit_letter_word_budget(
    letter: str,
    *,
    min_words: int = LETTER_MIN_WORDS,
    max_words: int = LETTER_MAX_WORDS,
) -> str:
    """Trim verbose boilerplate while keeping ERISA surface blocks and flaw text."""
    body, tail = _split_protected_letter_tail(letter)
    out = repair_denial_letter_artifacts(body)
    out = _DUPE_PARA_RE.sub(
        "\n\nStandard criteria apply regardless of information previously sent to the plan.",
        out,
    )
    for old, new in _LETTER_TRIMS:
        if word_count(out) <= max_words:
            break
        if old in out:
            out = out.replace(old, new, 1)

    while word_count(out) > max_words and "Specifically, the information provided" in out:
        out = out.replace(
            "Specifically, the information provided does not satisfy the "
            "utilization-management requirements associated with ",
            "The file does not satisfy utilization-management requirements for ",
            1,
        )
        if word_count(out) > max_words:
            # Drop the Specifically paragraph entirely (EXPLANATION still has rationale).
            start = out.find("Specifically, the information provided")
            if start == -1:
                break
            end = out.find("\n\n", start + 1)
            if end == -1:
                break
            out = out[:start] + out[end + 2 :]

    if word_count(out) > max_words:
        out = re.sub(
            r"\nFunding: This determination applies under your employer's self-funded "
            r"group arrangement \([^)]+\)\.",
            "",
            out,
            count=1,
        )

    if word_count(out) > max_words:
        out = out.replace(
            "subject to applicable federal and state requirements. ",
            "",
            1,
        )

    if word_count(out) < min_words:
        out += (
            "\n\nAdditional plan language regarding experimental/investigational "
            "definitions, network status, and member cost-sharing may apply and "
            "is available upon request."
        )
    if tail:
        return (out.strip() + tail).strip()
    return out.strip()
