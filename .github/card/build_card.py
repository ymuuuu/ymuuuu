#!/usr/bin/env python3
"""Rebuild terminal-card.svg: the neofetch-style header plus the user's top
public repos by stars, read live from the GitHub API.

Usage: build_card.py <card.json> <output.svg>
GITHUB_TOKEN is used when set (higher rate limit); public data needs none.
"""
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
CHAR_W = 8.4          # advance of one 14px monospace glyph
LEFT = 26.0
WIDTH = 640
NAME_COLS = 24        # "├── " plus the name, padded
STAR_COLS = 6         # "★ 999" plus a space
DESC_MAX = int((WIDTH - LEFT - (NAME_COLS + STAR_COLS) * CHAR_W - 16) / CHAR_W)
LOGO = [
    "██╗   ██╗  ███╗   ███╗  ██╗   ██╗  ██╗   ██╗",
    "╚██╗ ██╔╝  ████╗ ████║  ██║   ██║  ██║   ██║",
    " ╚████╔╝   ██╔████╔██║  ██║   ██║  ██║   ██║",
    "  ╚██╔╝    ██║╚██╔╝██║  ╚██╗ ██╔╝  ╚██╗ ██╔╝",
    "     ╚═╝   ██║ ╚═╝ ██║   ╚═══╝      ╚═══╝   ",
]


def fetch_repos(user):
    repos, page = [], 1
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-card"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    while True:
        url = "https://api.github.com/users/%s/repos?type=owner&per_page=100&page=%d" % (user, page)
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as resp:
            batch = json.load(resp)
        if not batch:
            return repos
        repos.extend(batch)
        page += 1


def shorten(text, limit):
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def top_repos(cfg):
    repos = [
        r for r in fetch_repos(cfg["user"])
        if not r["fork"] and not r["archived"] and not r["private"]
        and r["name"] not in cfg.get("exclude", [])
    ]
    repos.sort(key=lambda r: (-r["stargazers_count"], r["name"].lower()))
    return repos[: cfg.get("count", 5)]


def text(x, y, body, fill, bold=False):
    weight = ' font-weight="600"' if bold else ""
    return '  <text x="%.1f" y="%d" fill="%s" font-family="%s" font-size="14"%s>%s</text>' % (
        x, y, fill, FONT, weight, escape(body))


def render(cfg, repos):
    rows = len(repos)
    height = 249 + 21 * rows  # 4 rows gives the original 333
    logo_x = (WIDTH - len(LOGO[0]) * CHAR_W) / 2
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
        'role="img" aria-label="%s neofetch card">' % (WIDTH, height, WIDTH, height, cfg["user"]),
        '  <rect x="0.5" y="0.5" width="%d" height="%d" rx="10" fill="#0d1117" stroke="#30363d"/>'
        % (WIDTH - 1, height - 1),
        '  <circle cx="22" cy="18" r="5" fill="#ff5f57"/>',
        '  <circle cx="40" cy="18" r="5" fill="#febc2e"/>',
        '  <circle cx="58" cy="18" r="5" fill="#28c840"/>',
        text(LEFT, 52, cfg["user"] + "@github", "#e6edf3", bold=True),
        text(LEFT, 73, "─" * 70, "#30363d"),
    ]
    for i, line in enumerate(LOGO):
        out.append(text(logo_x, 98 + 21 * i, line, "#F7E647"))
    out.append(text(LEFT, 211, "top repos", "#e6edf3", bold=True))
    star_x = LEFT + NAME_COLS * CHAR_W
    desc_x = star_x + STAR_COLS * CHAR_W
    for i, r in enumerate(repos):
        branch = "└── " if i == rows - 1 else "├── "
        name = shorten(r["name"], NAME_COLS - 5)
        stars = r["stargazers_count"]
        star = "★%4d" % stars if stars else ""
        desc = shorten(cfg.get("descriptions", {}).get(r["name"]) or r["description"], DESC_MAX)
        out.append(
            '  <text y="%d" font-family="%s" font-size="14">'
            '<tspan x="%.1f" fill="#c9d1d9">%s</tspan>'
            '<tspan x="%.1f" fill="#F7E647">%s</tspan>'
            '<tspan x="%.1f" fill="#8b949e">· %s</tspan></text>'
            % (232 + 21 * i, FONT, LEFT, escape(branch + name), star_x, escape(star),
               desc_x, escape(desc)))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    cfg_path, out_path = sys.argv[1], sys.argv[2]
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)
    svg = render(cfg, top_repos(cfg))
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
