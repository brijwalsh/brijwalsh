"""Shared quarantine + client-mapping + redaction logic for the eod-drafter
test harness. Stdlib only.

This is a line-for-line transcription of the Python snippet in
`SKILL.md` §"3d. Client-domain quarantine (do this before §4)" plus the
title/summary/next_steps/participants_public overwrite that follows it.
If SKILL.md's algorithm ever changes, this module (and the fixtures that
depend on it) need to change too -- this file is not an independent
reimplementation, it is the test harness's copy of the spec.

Post-#eod-quarantine-gaps-0428 (PR #10) state: SKILL.md §3d now runs
five OR-ed signals, not four. The fifth is the title-alias check
(`alias_hit`), which scans title + summary + Granola notes for any
`title_hint` in the built-in alias table (goengen.com -> enGen/EnGen,
natera.com -> Natera/Panorama/Signatera/Prospera) extended by the
optional $CLIENT_TITLE_ALIASES env var. That catches internal-only
titles like "enGen QBR" and summaries that mention client domains
without any client-domain attendee.
"""

from __future__ import annotations

import json
import os

DEFAULT_CLIENT_DOMAINS = ["natera.com", "goengen.com"]

# Built-in marketing-name / product-name hints per client domain. Kept
# in sync with the DEFAULT_TITLE_ALIASES table in SKILL.md §3d.
DEFAULT_TITLE_ALIASES = {
    "goengen.com": ["enGen", "EnGen"],
    "natera.com": ["Natera", "Panorama", "Signatera", "Prospera"],
}

# Client-mapping test only: the short workstream key each client domain
# maps to. This key is NOT part of SKILL.md's quarantine snippet (which
# only ever produces a "dominant" *domain* string, e.g. "natera.com"); it
# mirrors the §4 workstream table ("natera" / "engen" cluster names).
CLIENT_KEY = {
    "natera.com": "natera",
    "goengen.com": "engen",
}


def host(email: str) -> str:
    # split on the last @ so "foo@bar@natera.com" still lands on natera.com
    return email.rsplit("@", 1)[-1].lower().strip()


def domain_hit(email: str, client_domains) -> bool:
    h = host(email)
    return any(h == d or h.endswith("." + d) for d in client_domains)


def matched_domains(email: str, client_domains) -> list:
    h = host(email)
    return [d for d in client_domains if h == d or h.endswith("." + d)]


def load_title_aliases(env: dict | None = None) -> dict:
    """Merge the built-in DEFAULT_TITLE_ALIASES table with any extension
    provided via $CLIENT_TITLE_ALIASES.

    Transcribed from SKILL.md §3d `load_title_aliases()`. Malformed JSON
    or wrong shape raises SystemExit — SKILL.md's contract is that a
    broken DLP table fails preflight closed. Tests that want to exercise
    the fail-closed path can pass `env={"CLIENT_TITLE_ALIASES": ...}`
    and catch SystemExit.
    """
    if env is None:
        env = os.environ
    table = {d.lower(): list(hints) for d, hints in DEFAULT_TITLE_ALIASES.items()}
    raw = (env.get("CLIENT_TITLE_ALIASES") or "").strip()
    if not raw:
        return table
    try:
        extra = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        raise SystemExit(
            "CLIENT_TITLE_ALIASES is not valid JSON — DM Brian and exit"
        )
    if not isinstance(extra, dict) or not all(
        isinstance(k, str)
        and isinstance(v, list)
        and all(isinstance(h, str) for h in v)
        for k, v in extra.items()
    ):
        raise SystemExit(
            "CLIENT_TITLE_ALIASES must be "
            '{"domain.com": ["Alias", ...]} — DM Brian and exit'
        )
    for domain, hints in extra.items():
        key = domain.lower()
        table.setdefault(key, [])
        table[key].extend(hints)
    return table


def quarantine_verdict(meeting: dict, client_domains=None, env: dict | None = None) -> dict:
    """Returns dict with keys: quarantined (bool), dominant (str),
    participant_hit, title_hit, folder_hit, unknown_attendance,
    alias_hit (bool each), matched_domains (sorted list of client domains
    hit via participants).

    Transcribed from SKILL.md §3d.
    """
    client_domains = client_domains or DEFAULT_CLIENT_DOMAINS
    title = (meeting.get("title") or "")

    participants = meeting.get("known_participants") or []
    participant_hit = any(
        domain_hit(p.get("email", ""), client_domains) for p in participants
    )

    title_hit = any(d.split(".")[0] in title.lower() for d in client_domains)

    folder_hit = (meeting.get("folder") or "").lower() in {
        "natera",
        "engen",
        "client-natera",
        "client-engen",
        "clients",
    }

    # fail-closed: no participants + no folder = we don't know, so quarantine
    unknown_attendance = not participants and not folder_hit

    # fifth signal: any title_hint from the alias table, case-insensitive,
    # in title OR summary OR Granola notes. Catches "enGen Sync — Nov 2026"
    # and internal-only "Prep for enGen QBR" (zero client attendees).
    title_aliases = load_title_aliases(env=env)
    haystack = " ".join([
        title,
        meeting.get("summary") or "",
        meeting.get("notes") or "",
    ]).lower()
    alias_hit = any(
        hint.lower() in haystack
        for hints in title_aliases.values()
        for hint in hints
    )

    client_hit = (
        participant_hit or title_hit or folder_hit
        or unknown_attendance or alias_hit
    )

    dominant = "unknown"
    if client_hit:
        dominant = next(
            (
                d
                for d in client_domains
                if any(
                    domain_hit(p.get("email", ""), client_domains)
                    and host(p.get("email", "")).endswith(d)
                    for p in participants
                )
                or d.split(".")[0] in title.lower()
                or any(
                    hint.lower() in haystack
                    for hint in title_aliases.get(d.lower(), [])
                )
            ),
            "unknown",
        )

    all_matched = sorted(
        {
            d
            for p in participants
            for d in matched_domains(p.get("email", ""), client_domains)
        }
    )

    return {
        "quarantined": client_hit,
        "dominant": dominant,
        "participant_hit": participant_hit,
        "title_hit": title_hit,
        "folder_hit": folder_hit,
        "unknown_attendance": unknown_attendance,
        "alias_hit": alias_hit,
        "matched_domains": all_matched,
    }


def map_client(meeting: dict, client_domains=None) -> str:
    """Meeting -> client key ("natera" / "engen" / "none").

    Based only on participant email domains (SKILL.md Rule 1), NOT on
    title/folder/summary signals -- this answers "whose meeting is this"
    for workstream-mapping purposes, which is a narrower question than
    "should this be quarantined".

    Pinned tie-break rule for ambiguous meetings (multiple client domains
    among participants): take the alphabetically-first matching domain
    string, then map that domain to its client key. E.g. a meeting with
    both natera.com and goengen.com participants maps to "engen" because
    "goengen.com" < "natera.com" alphabetically. This rule is arbitrary
    but deterministic; pin it here rather than re-deriving it per test.
    """
    client_domains = client_domains or DEFAULT_CLIENT_DOMAINS
    participants = meeting.get("known_participants") or []
    matched = sorted(
        {
            d
            for p in participants
            for d in matched_domains(p.get("email", ""), client_domains)
        }
    )
    if not matched:
        return "none"
    return CLIENT_KEY.get(matched[0], matched[0])


def redact_for_gateway(meeting: dict, client_domains=None) -> dict:
    """The "stripped for gateway" transform SKILL.md §3d applies to a
    quarantined meeting, extended with the metadata SKILL.md leaves
    untouched (duration/meeting_id/time/link) so downstream drafting can
    still say "3 client calls totaling 2h30m" without any meeting body
    leaking.

    Per SKILL.md §3d exactly:
      - title      -> f"Client sync ({dominant})" (ALWAYS overwritten for
                      every quarantined meeting -- there is no "keep
                      title if it has no client hints" branch in
                      SKILL.md; every quarantined title is templated the
                      same way regardless of what the original title
                      said)
      - summary    -> None
      - next_steps -> None
      - known_participants -> [] (SKILL.md calls this participants_public)
      - quarantined -> True

    Extended here (not literal SKILL.md text, but consistent with its
    "no meeting body leaves Slack" intent and needed to answer "how many
    client calls / how long"):
      - summary/next_steps rendered as the display placeholder
        "[redacted: client-domain meeting]" instead of null, for
        human-readable review
      - attendees -> count of the original known_participants (not the
        list itself)
      - duration_minutes / start_time / end_time / meeting_id /
        granola_link preserved verbatim -- SKILL.md §3d never touches
        these fields
    """
    client_domains = client_domains or DEFAULT_CLIENT_DOMAINS
    verdict = quarantine_verdict(meeting, client_domains)
    if not verdict["quarantined"]:
        return dict(meeting)

    participants = meeting.get("known_participants") or []
    return {
        "meeting_id": meeting.get("meeting_id"),
        "title": f"Client sync ({verdict['dominant']})",
        "summary": "[redacted: client-domain meeting]",
        "next_steps": "[redacted: client-domain meeting]",
        "attendees": len(participants),
        "duration_minutes": meeting.get("duration_minutes"),
        "start_time": meeting.get("start_time"),
        "end_time": meeting.get("end_time"),
        "granola_link": meeting.get("granola_link"),
        "quarantined": True,
    }
