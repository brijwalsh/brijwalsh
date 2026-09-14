"""TOP_3 split + merge test for eod-drafter §7e.

Simulates the LLM output and the PDP-surfaced targets, then runs the
mechanical split/merge described in `eod-drafter/SKILL.md §7e`. Proves:

- The `---TOP_3_HUMAN_ACTIONS---` marker splits draft from top-3.
- Overdue PDP targets always take priority over LLM bullets.
- Due-soon PDP targets fill next.
- LLM bullets fill the remainder without duplicating.
- Missing-marker input still produces a draft (fallback path).
- Cap is exactly 3 lines.

No LLM call. No gateway. Stdlib only.
"""

from __future__ import annotations

import re
import sys
from datetime import date, timedelta


MARKER = "---TOP_3_HUMAN_ACTIONS---"


def split_output(llm_text: str) -> tuple[str, str]:
    if MARKER in llm_text:
        draft, top3 = llm_text.split(MARKER, 1)
        return draft.strip(), top3.strip()
    return llm_text.strip(), ""


def clean_bullet(line: str) -> str:
    stripped = line.strip()
    return re.sub(r"^[0-9]+[.)]\s*|^[-•*]\s*", "", stripped)


def _normalize(text: str) -> str:
    """Lowercased alnum-only fingerprint for dedup."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _target_from_line(line: str) -> str:
    """Strip `:warning: ` prefix and the trailing ` (due ..., evidence: ...)`.

    So a PDP-formatted line and the LLM's plain bullet compare on the
    same substring."""
    line = re.sub(r"^:warning:\s*", "", line)
    line = re.sub(r"\s*\(due \d{4}-\d{2}-\d{2}, evidence:.*\)\s*$", "", line)
    return line.strip()


def _already_present(candidate: str, existing: list[str]) -> bool:
    cand_norm = _normalize(_target_from_line(candidate))
    if not cand_norm:
        return True
    for line in existing:
        line_norm = _normalize(_target_from_line(line))
        if cand_norm == line_norm:
            return True
        if len(cand_norm) >= 20 and cand_norm in line_norm:
            return True
        if len(line_norm) >= 20 and line_norm in cand_norm:
            return True
    return False


def merge_top3(
    pdp_surfaced: list[dict],
    llm_top3_raw: str,
    today: date,
) -> list[str]:
    overdue = [t for t in pdp_surfaced if date.fromisoformat(t["Due"]) < today]
    due_soon = [
        t for t in pdp_surfaced
        if today <= date.fromisoformat(t["Due"]) <= today + timedelta(days=1)
    ]
    other = [
        t for t in pdp_surfaced
        if date.fromisoformat(t["Due"]) > today + timedelta(days=1)
    ]

    def to_line(t: dict) -> str:
        prefix = ":warning: " if date.fromisoformat(t["Due"]) < today else ""
        return f"{prefix}{t['Target']} (due {t['Due']}, evidence: {t['Evidence source']})"

    llm_bullets = [clean_bullet(ln) for ln in llm_top3_raw.splitlines() if ln.strip()]
    llm_bullets = [b for b in llm_bullets if b]

    top3: list[str] = []
    for t in overdue + due_soon:
        if len(top3) >= 3:
            break
        line = to_line(t)
        if not _already_present(line, top3):
            top3.append(line)
    for b in llm_bullets:
        if len(top3) >= 3:
            break
        if not _already_present(b, top3):
            top3.append(b)
    for t in other:
        if len(top3) >= 3:
            break
        line = to_line(t)
        if not _already_present(line, top3):
            top3.append(line)
    return top3[:3]


FIXTURE_LLM_OUTPUT = """Today
:pullreq: Landed #45 (Google T1)
:test_tube: Ran multi-model review of infra <https://…|#1>

Tomorrow
:pullreq: Finish Anmol's CI quality-gate <https://…|#53>
:test_tube: Push infra <https://…|#1> findings to resolution with Anmol
:dashboard: Teach Metabase view-building to the team

*Sent using* <@U093DJ468EN|Cursor>

---TOP_3_HUMAN_ACTIONS---
1. Finish review and land Anmol's CI quality-gate <https://…|#53>
2. Push infra <https://…|#1> findings to resolution with Anmol
3. Teach Metabase view-building session with the team
"""


def _pdp(id_, target, due, source, status="in-progress"):
    return {
        "ID": id_,
        "Target": target,
        "Due": due,
        "Status": status,
        "Evidence source": source,
    }


def test_basic_split() -> None:
    draft, top3_raw = split_output(FIXTURE_LLM_OUTPUT)
    assert "Today" in draft and "Tomorrow" in draft, "draft lost content"
    assert "---" not in draft, "marker leaked into draft"
    assert "1. Finish review" in top3_raw, "top3 section not captured"
    assert MARKER not in top3_raw, "marker leaked into top3"
    print("  test_basic_split OK")


def test_no_marker_fallback() -> None:
    draft_only = "Today\n• foo\nTomorrow\n• bar"
    draft, top3_raw = split_output(draft_only)
    assert draft == draft_only.strip()
    assert top3_raw == ""
    print("  test_no_marker_fallback OK")


def test_overdue_pdp_takes_priority() -> None:
    today = date(2026, 9, 15)
    pdp = [
        _pdp(
            "pdp-2026-w37-01",
            "Overdue Directive: enGen staffing decision",
            "2026-09-12",
            "#the-staffing-conversation",
        ),
    ]
    _, top3_raw = split_output(FIXTURE_LLM_OUTPUT)
    top3 = merge_top3(pdp, top3_raw, today)
    assert len(top3) == 3
    assert top3[0].startswith(":warning: Overdue Directive"), (
        f"overdue PDP not first: {top3[0]!r}"
    )
    print("  test_overdue_pdp_takes_priority OK")


def test_due_tomorrow_takes_priority_over_llm() -> None:
    today = date(2026, 9, 15)
    pdp = [
        _pdp(
            "pdp-2026-w38-01",
            "Kevin/Chelsea sync ask",
            "2026-09-16",
            "#chelsea-dm",
        ),
    ]
    _, top3_raw = split_output(FIXTURE_LLM_OUTPUT)
    top3 = merge_top3(pdp, top3_raw, today)
    assert len(top3) == 3
    assert "Kevin/Chelsea sync ask" in top3[0]
    assert not top3[0].startswith(":warning:"), "not overdue, no warning"
    print("  test_due_tomorrow_takes_priority_over_llm OK")


def test_no_pdp_uses_llm_only() -> None:
    today = date(2026, 9, 15)
    _, top3_raw = split_output(FIXTURE_LLM_OUTPUT)
    top3 = merge_top3([], top3_raw, today)
    assert len(top3) == 3
    assert "Anmol's CI quality-gate" in top3[0]
    print("  test_no_pdp_uses_llm_only OK")


def test_cap_is_three() -> None:
    today = date(2026, 9, 15)
    pdp = [
        _pdp(f"pdp-w{i}", f"Target {i}", "2026-09-14", "src")
        for i in range(5)
    ]
    _, top3_raw = split_output(FIXTURE_LLM_OUTPUT)
    top3 = merge_top3(pdp, top3_raw, today)
    assert len(top3) == 3, f"expected 3, got {len(top3)}"
    print("  test_cap_is_three OK")


def test_empty_run() -> None:
    today = date(2026, 9, 15)
    top3 = merge_top3([], "", today)
    assert top3 == [], "empty-in should be empty-out"
    print("  test_empty_run OK")


def test_no_duplicates_when_llm_repeats_pdp_target() -> None:
    today = date(2026, 9, 15)
    pdp = [
        _pdp(
            "pdp-repeat",
            "Push infra <https://…|#1> findings to resolution with Anmol",
            "2026-09-16",
            "GH PR #1",
        ),
    ]
    _, top3_raw = split_output(FIXTURE_LLM_OUTPUT)
    top3 = merge_top3(pdp, top3_raw, today)
    assert len(top3) == 3
    seen = [ln for ln in top3 if "Push infra" in ln]
    assert len(seen) == 1, f"duplicate PDP+LLM bullet: {top3}"
    print("  test_no_duplicates_when_llm_repeats_pdp_target OK")


def main() -> int:
    for fn in [
        test_basic_split,
        test_no_marker_fallback,
        test_overdue_pdp_takes_priority,
        test_due_tomorrow_takes_priority_over_llm,
        test_no_pdp_uses_llm_only,
        test_cap_is_three,
        test_empty_run,
        test_no_duplicates_when_llm_repeats_pdp_target,
    ]:
        fn()
    print("\ntest_top3_split: 8 passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
