"""Custom MLflow scorers for COMPASS eval.

Currently:
  - policy_citation_present: fails any KA-routed turn that lacks at least
    one KA-* doc_id citation in the answer.

These are wired into the evaluation harness (see eval/README.md) and into
the nightly production-trace monitoring job.
"""

from __future__ import annotations

import re

from mlflow.genai.scorers import scorer

# Matches doc IDs from ka-corpus/*.md frontmatter, e.g. KA-HANDBOOK-001.
_CITATION_RE = re.compile(r"\bKA-[A-Z]+-\d{3}\b")


@scorer
def policy_citation_present(
    outputs: str,
    expectations: dict,
) -> bool:
    """True iff a citation is present when the turn requires one.

    A turn requires a citation when:
      - expectations.expected_tool == "ka", OR
      - expectations.must_cite_corpus is true
    """
    requires_citation = (
        expectations.get("expected_tool") == "ka"
        or expectations.get("must_cite_corpus") is True
    )
    if not requires_citation:
        return True  # not applicable -> pass
    return bool(_CITATION_RE.search(outputs or ""))
