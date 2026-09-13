#!/usr/bin/env python3
"""Classify and rank eyes fixtures. Stdlib only. No Slack or LLM calls."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
RESULTS_PATH = FIXTURES / "search_results.json"
EXPECTED_V0_1_PATH = FIXTURES / "expected_ranking.json"
DEDUP_STATE_PATH = FIXTURES / "dedup_state.json"
EXPECTED_V0_2_PATH = FIXTURES / "expected_ranking_v0_2.json"

# Frozen "now" so fixture ages stay stable.
DEFAULT_NOW_TS = 1789354800.0

PR_RE = re.compile(r"github\.com/[^/]+/[^/]+/pull/\d+")
DOC_RE = re.compile(r"(notion\.so|confluence|docs\.google\.com|liatr\.io)")
URL_RE = re.compile(
    r"<(https?://[^|>]+)(?:\|[^>]*)?>|(?<!<)(https?://[^\s>|]+)"
)
LIATRIO_OR_GITHUB_RE = re.compile(r"(github\.com|liatrio\.com|liatr\.io)")


def extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    for match in URL_RE.finditer(text):
        urls.append(match.group(1) or match.group(2))
    return urls


def classify(item: dict) -> str:
    text = item.get("text") or ""
    if PR_RE.search(text):
        return "pr"
    if DOC_RE.search(text):
        return "doc"
    urls = extract_urls(text)
    if len(urls) == 1 and not LIATRIO_OR_GITHUB_RE.search(text):
        return "article"
    try:
        replies = int(item.get("reply_count") or 0)
    except (TypeError, ValueError):
        replies = 0
    if replies >= 3:
        return "thread"
    return "msg"


def channel_name(item: dict) -> str:
    channel = item.get("channel") or {}
    return (channel.get("name") or "").lstrip("#")


def is_work_channel(item: dict) -> bool:
    name = channel_name(item)
    return name.startswith("client-") or name.startswith("project-")


def age_seconds(item: dict, now_ts: float) -> float:
    return now_ts - float(item["ts"])


def rank_key_v0_1(item: dict, now_ts: float) -> tuple:
    """Return the v0.1 close-the-loop ranking key."""
    return (
        item["_class"] in ("pr", "doc"),
        age_seconds(item, now_ts) > 5 * 86400,
        is_work_channel(item),
        float(item["ts"]),
    )


def parse_timestamp(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def awareness_seconds(item: dict, now_ts: float, dedup_index: dict) -> float:
    row = dedup_index.get(item["permalink"])
    if not row:
        return 0.0
    return max(0.0, now_ts - parse_timestamp(row["first_seen_ts"]))


def rank_key_v0_2(item: dict, now_ts: float, dedup_index: dict) -> tuple:
    """Return the v0.2 key: awareness first, then the v0.1 rules."""
    return (
        awareness_seconds(item, now_ts, dedup_index),
        *rank_key_v0_1(item, now_ts),
    )


def load_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def format_row(
    item: dict,
    now_ts: float,
    dedup_index: dict | None = None,
) -> str:
    slack_age_days = age_seconds(item, now_ts) / 86400
    channel = channel_name(item) or (
        f"<no name {item.get('channel', {}).get('id', '?')}>"
    )
    awareness = ""
    if dedup_index is not None:
        days = awareness_seconds(item, now_ts, dedup_index) / 86400
        awareness = f"  awareness={days:.1f}d"
    return (
        f"{item.get('iid')}  class={item.get('_class')}"
        f"{awareness}  slack_age={slack_age_days:.1f}d"
        f"  channel={channel}  ts={item.get('ts')}"
    )


def validate_results(results) -> bool:
    if isinstance(results, list) and len(results) == 20:
        return True
    length = len(results) if isinstance(results, list) else "?"
    print(
        "search_results.json must be a 20-item array, got "
        f"{type(results).__name__} len={length}",
        file=sys.stderr,
    )
    return False


def annotate(results: list[dict]) -> list[dict]:
    annotated = []
    for item in results:
        row = dict(item)
        row["_class"] = classify(item)
        annotated.append(row)
    return annotated


def check_ranking(
    *,
    version: str,
    results: list[dict],
    expected_path: Path,
    dedup_index: dict | None = None,
) -> int:
    expected_doc = load_json(expected_path)
    now_ts = float(expected_doc.get("as_of_ts", DEFAULT_NOW_TS))
    expected = [row["iid"] for row in expected_doc["top_5"]]
    ranked = annotate(results)

    if version == "v0.1":
        ranked.sort(key=lambda item: rank_key_v0_1(item, now_ts), reverse=True)
    else:
        if dedup_index is None:
            raise ValueError("v0.2 ranking requires a dedup index")
        ranked.sort(
            key=lambda item: rank_key_v0_2(item, now_ts, dedup_index),
            reverse=True,
        )

    got = [item["iid"] for item in ranked[:5]]
    fixture_name = expected_path.name
    if got == expected:
        print(f"{version} top-5 matches {fixture_name} (5/5)")
        for position, item in enumerate(ranked[:5], start=1):
            print(
                f"  {position}. "
                f"{format_row(item, now_ts, dedup_index)}"
            )
        return 0

    print(f"{version} top-5 ranking mismatch", file=sys.stderr)
    print("expected:", file=sys.stderr)
    by_iid = {item["iid"]: item for item in ranked}
    for position, iid in enumerate(expected, start=1):
        item = by_iid.get(iid)
        if item is None:
            print(f"  {position}. {iid}  (not in fixture)", file=sys.stderr)
        else:
            print(
                f"  {position}. {format_row(item, now_ts, dedup_index)}",
                file=sys.stderr,
            )
    print("got:", file=sys.stderr)
    for position, item in enumerate(ranked[:5], start=1):
        marker = "" if item["iid"] == expected[position - 1] else "  <--"
        print(
            f"  {position}. {format_row(item, now_ts, dedup_index)}{marker}",
            file=sys.stderr,
        )
    return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        choices=("v0.1", "v0.2", "all"),
        default="all",
        help="ranking path to verify; default checks both",
    )
    parser.add_argument(
        "--dedup-state",
        type=Path,
        default=DEDUP_STATE_PATH,
        help="optional v0.2 dedup-state fixture",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = load_json(RESULTS_PATH)
    if not validate_results(results):
        return 2

    exit_codes: list[int] = []
    if args.version in ("v0.1", "all"):
        exit_codes.append(
            check_ranking(
                version="v0.1",
                results=results,
                expected_path=EXPECTED_V0_1_PATH,
            )
        )

    if args.version in ("v0.2", "all"):
        dedup_doc = load_json(args.dedup_state)
        dedup_index = dedup_doc.get("by_permalink", dedup_doc)
        if not isinstance(dedup_index, dict):
            print("dedup-state fixture must contain a by_permalink object", file=sys.stderr)
            return 2
        exit_codes.append(
            check_ranking(
                version="v0.2",
                results=results,
                expected_path=EXPECTED_V0_2_PATH,
                dedup_index=dedup_index,
            )
        )

    return max(exit_codes, default=0)


if __name__ == "__main__":
    sys.exit(main())
