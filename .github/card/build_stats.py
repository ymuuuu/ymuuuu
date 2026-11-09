#!/usr/bin/env python3
"""Write stats.svg and langs.svg for the profile README from the GitHub
GraphQL API. Replaces the github-readme-stats cards, whose shared public
server is not reliably up.

Usage: build_stats.py <card.json> <stats.svg> <langs.svg>
Needs GITHUB_TOKEN (GraphQL refuses anonymous requests).
"""
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

FONT = "'Segoe UI',Ubuntu,'Helvetica Neue',Sans-Serif"
BG, TITLE, TEXT, MUTED = "#0d1117", "#F7E647", "#c9d1d9", "#8b949e"
HEIGHT = 165
TOP_LANGS = 6

QUERY = """
query($login: String!) {
  user(login: $login) {

    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection { totalCommitContributions restrictedContributionsCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      nodes {
        name
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def graphql(login):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                 "User-Agent": "profile-card"})
    with urllib.request.urlopen(req) as resp:
        body = json.load(resp)
    if body.get("errors"):
        raise SystemExit("GraphQL error: %s" % body["errors"])
    return body["data"]["user"]


def frame(width, title):
    return [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
        'role="img" aria-label="%s">' % (width, HEIGHT, width, HEIGHT, escape(title)),
        '  <rect x="0" y="0" width="%d" height="%d" rx="6" fill="%s"/>' % (width, HEIGHT, BG),
        '  <text x="25" y="35" fill="%s" font-family="%s" font-size="18" font-weight="600">%s</text>'
        % (TITLE, FONT, escape(title)),
    ]


def stats_svg(user, login, exclude):
    repos = [r for r in user["repositories"]["nodes"] if r["name"] not in exclude]
    cc = user["contributionsCollection"]
    rows = [
        ("★", "Total stars", sum(r["stargazerCount"] for r in repos)),
        ("●", "Commits (last year)", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
        ("⇄", "Pull requests", user["pullRequests"]["totalCount"]),
        ("!", "Issues", user["issues"]["totalCount"]),
        ("◆", "Contributed to (last year)", user["repositoriesContributedTo"]["totalCount"]),
    ]
    width = 400
    out = frame(width, "%s's GitHub stats" % login)
    for i, (icon, label, value) in enumerate(rows):
        y = 64 + 22 * i
        out.append('  <text x="25" y="%d" fill="%s" font-family="%s" font-size="14">%s</text>'
                   % (y, TITLE, FONT, escape(icon)))
        out.append('  <text x="47" y="%d" fill="%s" font-family="%s" font-size="14" font-weight="600">%s:</text>'
                   % (y, TEXT, FONT, escape(label)))
        out.append('  <text x="%d" y="%d" fill="%s" font-family="%s" font-size="14" font-weight="700" '
                   'text-anchor="end">%s</text>' % (width - 25, y, TEXT, FONT, "{:,}".format(value)))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def langs_svg(user, exclude):
    sizes, colors = {}, {}
    for r in user["repositories"]["nodes"]:
        if r["name"] in exclude:
            continue
        for e in r["languages"]["edges"]:
            name = e["node"]["name"]
            sizes[name] = sizes.get(name, 0) + e["size"]
            colors[name] = e["node"]["color"] or MUTED
    total = sum(sizes.values()) or 1
    top = sorted(sizes.items(), key=lambda kv: -kv[1])[:TOP_LANGS]
    shown = sum(s for _, s in top) or 1
    width, bar_w = 300, 250
    out = frame(width, "Most used languages")
    out.append('  <clipPath id="bar"><rect x="25" y="52" width="%d" height="8" rx="4"/></clipPath>' % bar_w)
    x = 25.0
    for name, size in top:
        w = bar_w * size / shown
        out.append('  <rect clip-path="url(#bar)" x="%.2f" y="52" width="%.2f" height="8" fill="%s"/>'
                   % (x, w, colors[name]))
        x += w
    for i, (name, size) in enumerate(top):
        col, row = i % 2, i // 2
        cx, cy = 25 + col * 135, 88 + row * 25
        out.append('  <circle cx="%d" cy="%d" r="5" fill="%s"/>' % (cx + 5, cy - 4, colors[name]))
        out.append('  <text x="%d" y="%d" fill="%s" font-family="%s" font-size="12">%s '
                   '<tspan fill="%s">%.1f%%</tspan></text>'
                   % (cx + 16, cy, TEXT, FONT, escape(name), MUTED, 100.0 * size / total))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    cfg_path, stats_path, langs_path = sys.argv[1:4]
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    login = cfg["user"]
    exclude = set(cfg.get("exclude", []))
    user = graphql(login)
    for path, svg in ((stats_path, stats_svg(user, login, exclude)),
                      (langs_path, langs_svg(user, exclude))):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)


if __name__ == "__main__":
    main()
