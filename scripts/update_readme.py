#!/usr/bin/env python3
"""Regenerate repository listing sections in README.md from the GitHub API."""

import json
import os
import re
import sys
import urllib.request
from fnmatch import fnmatch

OWNER = "conallob"
README = "README.md"
API_BASE = "https://api.github.com"

# Repos that should not appear in any section.
# Covers personal websites, config-only repos, learning repos, and old/archived work.
EXCLUDE = frozenset({
    ".github",
    "conallob",
    "conallob.github.io",
    "gerry.obrien.fyi",
    "publications.conall.net",
    "portfolio.conall.dev",
    "www.conall.net",
    "blog.conall.net",
    "misc",
    "PreviousCodingInterviews",
    "AdventOfCodeSolutions",
    "college-notes",
    "personal-scm-snapshot",
    "personio-technical-interview",
    "aws-terraform-playground",
    "Home-Assistant-Config",
    "Home-Assistant-Meadow-Close",
    "ssh",
    "ssh-config",
    "Tailscale-Configs",
    "private-scripts",
    "private_scripts",
    "New-Machine",
    "CICD-Patterns",
    "SRE-Reference-Docs",
    "cv",
    "professional-artifacts",
    "Keyboardio-Configuration",
})

# Ordered list of categories. Each repo is assigned to the first category it matches.
# Pattern matching uses fnmatch glob syntax. Explicit lists are checked first within
# each category. The final entry acts as a catch-all for any remaining repos that
# have a description.
CATEGORIES = [
    {
        "marker": "MCP_SERVERS",
        "patterns": ["mcp-*"],
        "explicit": [],
    },
    {
        "marker": "HA_INTEGRATIONS",
        "patterns": ["homeassistant-*"],
        "explicit": [],
    },
    {
        "marker": "HA_ADDONS",
        "patterns": ["hassio-*"],
        "explicit": ["ireland-electricity-tariffs"],
    },
    {
        "marker": "SRE_TOOLS",
        "patterns": [],
        "explicit": ["alert-glow", "o11y-analysis-tools", "outalator", "silence-manager"],
    },
    {
        "marker": "OTHER_PROJECTS",
        "patterns": ["*"],
        "explicit": [],
    },
]


def fetch_repos(token: str) -> list:
    repos = []
    page = 1
    while True:
        url = f"{API_BASE}/users/{OWNER}/repos?type=public&per_page=100&page={page}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urllib.request.urlopen(req) as resp:
            batch = json.loads(resp.read())
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def categorize(repos: list) -> dict:
    buckets = {cat["marker"]: [] for cat in CATEGORIES}
    assigned = set()

    for cat in CATEGORIES:
        for repo in repos:
            name = repo["name"]
            if name in assigned or repo.get("archived") or name in EXCLUDE:
                continue
            desc = repo.get("description") or ""

            matched = name in cat["explicit"] or any(fnmatch(name, p) for p in cat["patterns"])
            if not matched:
                continue
            # Catch-all requires a description to avoid noise from stub repos
            if cat["marker"] == "OTHER_PROJECTS" and not desc.strip():
                continue

            buckets[cat["marker"]].append(repo)
            assigned.add(name)

    for marker in buckets:
        buckets[marker].sort(key=lambda r: r["name"].lower())

    return buckets


def make_table(repos: list) -> str:
    lines = ["| Repository | Description |", "|---|---|"]
    for repo in repos:
        name = repo["name"]
        desc = (repo.get("description") or "").strip()
        url = repo["html_url"]
        lines.append(f"| [{name}]({url}) | {desc} |")
    return "\n".join(lines) + "\n"


def update_section(content: str, marker: str, repos: list) -> str:
    table = make_table(repos)
    pattern = rf"(<!-- {marker}_START -->\n).*?(<!-- {marker}_END -->)"
    replacement = rf"\g<1>{table}\2"
    updated = re.sub(pattern, replacement, content, flags=re.DOTALL)
    if updated == content:
        print(f"  WARNING: marker {marker} not found in README", file=sys.stderr)
    return updated


def main():
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("GITHUB_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    repos = fetch_repos(token)
    print(f"Fetched {len(repos)} public repos")

    buckets = categorize(repos)

    with open(README) as f:
        content = f.read()

    for cat in CATEGORIES:
        marker = cat["marker"]
        content = update_section(content, marker, buckets[marker])
        print(f"  {marker}: {len(buckets[marker])} repos")

    with open(README, "w") as f:
        f.write(content)

    print(f"Updated {README}")


if __name__ == "__main__":
    main()
