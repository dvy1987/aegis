from __future__ import annotations

import re

from app.aegis_v1.tools import DISCLAIMER

_GUARANTEE_RE = re.compile(r"\b(will win|guaranteed(?:\s+to)?\s+(?:win|overturn|approve))\b", re.IGNORECASE)


def apply_guardrails(letter_body: str, allowed_doc_ids: set[str]) -> str:
    """Make any LLM letter body deterministically safe.

    - guarantee/win-claim language softened
    - exclamation marks removed
    - canonical disclaimer ensured (prepended if missing)
    Citation enforcement is handled structurally in the drafter (only
    `allowed_doc_ids` are attached to `citations_used`); this filter scrubs the
    prose. `allowed_doc_ids` is accepted for future prose-citation scrubbing.
    """
    text = _GUARANTEE_RE.sub("may support the request", letter_body)
    text = text.replace("!", ".")
    if DISCLAIMER.lower() not in text.lower():
        text = f"{DISCLAIMER} This is a draft for review by a person before filing.\n\n{text}"
    return text.strip()
