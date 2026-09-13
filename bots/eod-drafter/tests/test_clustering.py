#!/usr/bin/env python3
"""Clustering tests for eod-drafter. Stdlib only. No gh, no Slack MCP.

Verifies:
- PRs (+ reviews) cluster by short repo name (SKILL.md \u00a73a /
  repository.nameWithOwner)
- Slack messages cluster by exact channel, tagged with a category derived
  from the channel-name prefix (SKILL.md \u00a73b / \u00a75 rule 1's #client-
  distinction)
- Known repos/channels with zero activity in the window are dropped from
  the output
"""

from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"


def load(name: str):
    with (FIXTURES / name).open(encoding="utf-8") as fh:
        return json.load(fh)


def short_repo(name_with_owner: str) -> str:
    return name_with_owner.rsplit("/", 1)[-1]


def channel_category(channel: str) -> str:
    if channel.startswith("#project-"):
        return "project"
    if channel.startswith("#client-"):
        return "client"
    return "other"


def cluster_github(gh: dict) -> tuple[list[dict], list[str]]:
    counts: "OrderedDict[str, int]" = OrderedDict()
    for repo in gh.get("known_repos", []):
        counts[repo] = 0

    for pr in gh.get("prs", []):
        repo = short_repo(pr["repository"]["nameWithOwner"])
        counts[repo] = counts.get(repo, 0) + 1

    for review in gh.get("reviews", []):
        repo = short_repo(review["pull_request"]["repository"]["nameWithOwner"])
        counts[repo] = counts.get(repo, 0) + 1

    clusters = [
        {"repo": repo, "count": count} for repo, count in counts.items() if count > 0
    ]
    dropped = [repo for repo, count in counts.items() if count == 0]
    return clusters, dropped


def cluster_slack(slack: dict) -> tuple[list[dict], list[str]]:
    counts: "OrderedDict[str, int]" = OrderedDict()
    for channel in slack.get("known_channels", []):
        counts[channel] = 0

    for msg in slack.get("messages", []):
        channel = msg["channel"]
        counts[channel] = counts.get(channel, 0) + 1

    clusters = [
        {"channel": channel, "category": channel_category(channel), "count": count}
        for channel, count in counts.items()
        if count > 0
    ]
    dropped = [channel for channel, count in counts.items() if count == 0]
    return clusters, dropped


def as_comparable(clusters: list[dict], keys: tuple[str, ...]) -> list[tuple]:
    return sorted(tuple(c[k] for k in keys) for c in clusters)


def main() -> int:
    gh_activity = load("gh_activity.json")
    slack_activity = load("slack_activity.json")
    expected = load("expected_clusters.json")

    gh_clusters, gh_dropped = cluster_github(gh_activity)
    slack_clusters, slack_dropped = cluster_slack(slack_activity)

    failures = []

    got_gh = as_comparable(gh_clusters, ("repo", "count"))
    want_gh = as_comparable(expected["github"], ("repo", "count"))
    if got_gh != want_gh:
        failures.append(f"github clusters mismatch: got={got_gh} want={want_gh}")

    if sorted(gh_dropped) != sorted(expected["github_dropped_empty"]):
        failures.append(
            f"github dropped-empty mismatch: got={sorted(gh_dropped)} "
            f"want={sorted(expected['github_dropped_empty'])}"
        )

    got_slack = as_comparable(slack_clusters, ("channel", "category", "count"))
    want_slack = as_comparable(
        expected["slack"], ("channel", "category", "count")
    )
    if got_slack != want_slack:
        failures.append(f"slack clusters mismatch: got={got_slack} want={want_slack}")

    if sorted(slack_dropped) != sorted(expected["slack_dropped_empty"]):
        failures.append(
            f"slack dropped-empty mismatch: got={sorted(slack_dropped)} "
            f"want={sorted(expected['slack_dropped_empty'])}"
        )

    if failures:
        print("clustering mismatch:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print(
        f"clustering OK: {len(gh_clusters)} github repo cluster(s) "
        f"({len(gh_dropped)} dropped empty), {len(slack_clusters)} slack "
        f"channel cluster(s) ({len(slack_dropped)} dropped empty)"
    )
    for c in gh_clusters:
        print(f"  github  {c['repo']}: {c['count']}")
    for c in slack_clusters:
        print(f"  slack   {c['channel']} [{c['category']}]: {c['count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
