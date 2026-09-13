#!/usr/bin/env python3
"""Classify + rank eyes search fixtures. Stdlib only. No Slack, no LLM."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "fixtures" / "search_results.json"
EXPECTED_PATH = ROOT / "fixtures" / "expected_ranking.json"

# Frozen "now" so fixture ages stay stable. Matches expected_ranking.json.
DEFAULT_NOW_TS = 1789354800.0  # 2026-09-13 22:00:00 America/Chicago

PR_RE = re.compile(r"github\.com/[^/]+/[^/]+/pull/\d+")
DOC_RE = re.compile(r"(notion\.so|confluence|docs\.google\.com|liatr\.io)")
# Slack <https://url|label> / <https://url>, or a bare URL.
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
    name = channel.get("name") or ""
    return name.lstrip("#")


def is_work_channel(item: dict) -> bool:
    name = channel_name(item)
    return name.startswith("client-") or name.startswith("project-")


def age_seconds(item: dict, now_ts: float) -> float:
    return now_ts - float(item["ts"])


def rank_key(item: dict, now_ts: float) -> tuple:
    cls = item["_class"]
    age = age_seconds(item, now_ts)
    # Sort descending: True/larger first. Negate ts so newest wins last.
    return (
        cls in ("pr", "doc"),
        age > 5 * 86400,
        is_work_channel(item),
        float(item["ts"]),
    )


def load_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def format_row(item: dict, now_ts: float) -> str:
    age_days = age_seconds(item, now_ts) / 86400
    ch = channel_name(item) or f"<no name {item.get('channel', {}).get('id', '?')}>"
    return (
        f"{item.get('iid')}  class={item.get('_class')}  "
        f"age={age_days:.1f}d  channel={ch}  ts={item.get('ts')}"
    )


def main() -> int:
    results = load_json(RESULTS_PATH)
    expected_doc = load_json(EXPECTED_PATH)
    now_ts = float(expected_doc.get("as_of_ts", DEFAULT_NOW_TS))
    expected = [row["iid"] for row in expected_doc["top_5"]]

    if not isinstance(results, list) or len(results) != 20:
        print(
            f"search_results.json must be a 20-item array, got "
            f"{type(results).__name__} len={len(results) if isinstance(results, list) else '?'}",
            file=sys.stderr,
        )
        return 2

    annotated = []
    for item in results:
        row = dict(item)
        row["_class"] = classify(item)
        annotated.append(row)

    annotated.sort(key=lambda item: rank_key(item, now_ts), reverse=True)
    got = [item["iid"] for item in annotated[:5]]

    if got == expected:
        print("top-5 matches expected_ranking.json (5/5)")
        for i, item in enumerate(annotated[:5], start=1):
            print(f"  {i}. {format_row(item, now_ts)}")
        return 0

    print("top-5 ranking mismatch", file=sys.stderr)
    print("expected:", file=sys.stderr)
    by_iid = {item["iid"]: item for item in annotated}
    for i, iid in enumerate(expected, start=1):
        item = by_iid.get(iid)
        if item is None:
            print(f"  {i}. {iid}  (not in fixture)", file=sys.stderr)
        else:
            print(f"  {i}. {format_row(item, now_ts)}", file=sys.stderr)
    print("got:", file=sys.stderr)
    for i, item in enumerate(annotated[:5], start=1):
        if i - 1 < len(expected) and item["iid"] == expected[i - 1]:
            mark = ""
        else:
            mark = "  <--"
        print(f"  {i}. {format_row(item, now_ts)}{mark}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
