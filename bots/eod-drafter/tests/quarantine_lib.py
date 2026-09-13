"""Shared quarantine + client-mapping + redaction logic for the eod-drafter
test harness. Stdlib only.

This is a line-for-line transcription of the Python snippet in
`SKILL.md` §"3d. Client-domain quarantine (do this before §4)" plus the
title/summary/next_steps/participants_public overwrite that follows it.
If SKILL.md's algorithm ever changes, this module (and the fixtures that
depend on it) need to change too -- this file is not an independent
reimplementation, it is the test harness's copy of the spec.

Do not add signals here that SKILL.md doesn't have. Known gaps
(documented per-fixture with a `TODO(#eod-quarantine-gaps-0428)` note)
are intentionally left unfixed so the tests keep asserting CURRENT
behavior, not aspirational behavior.
"""

from __future__ import annotations

DEFAULT_CLIENT_DOMAINS = ["natera.com", "goengen.com"]

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


def quarantine_verdict(meeting: dict, client_domains=None) -> dict:
    """Returns dict with keys: quarantined (bool), dominant (str),
    participant_hit, title_hit, folder_hit, unknown_attendance (bool each),
    matched_domains (sorted list of client domains hit via participants).

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

    client_hit = participant_hit or title_hit or folder_hit or unknown_attendance

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
