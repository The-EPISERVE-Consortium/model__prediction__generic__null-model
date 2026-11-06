#!/usr/bin/env python3
"""Rebuild the LLM indexes after editing or regenerating the documentation.

Generates:
  documentation/llms-full.txt
  documentation/public/llms-full.txt   (served at /llms-full.txt)
  documentation/public/llms.txt        (served at /llms.txt)

Relative links are rewritten to absolute site URLs for pages, and to GitHub
blob URLs for repository files, so the served copies do not contain broken
`../` paths.
"""

from __future__ import annotations

import posixpath
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # documentation/
REPO = "https://github.com/The-EPISERVE-Consortium/model__prediction__generic__null-model"
SITE = "https://the-episerve-consortium.github.io/model__prediction__generic__null-model"

PAGES = [
    ("Contributor Guide", "onboarding/contributor-guide.md"),
    ("Staff Engineer Guide", "onboarding/staff-engineer-guide.md"),
    ("Executive Guide", "onboarding/executive-guide.md"),
    ("Product Manager Guide", "onboarding/product-manager-guide.md"),
    ("Overview", "01-getting-started/overview.md"),
    ("Container Contract", "01-getting-started/container-contract.md"),
    ("Configuration", "01-getting-started/configuration.md"),
    ("Local Development", "01-getting-started/local-development.md"),
    ("Execution Pipeline", "02-architecture/execution-pipeline.md"),
    ("Time Axis and Target Handling", "02-architecture/series-handling.md"),
    ("The Null Forecast", "02-architecture/null-forecast.md"),
    ("Model Card and Config Validation", "02-architecture/model-card-and-validation.md"),
    ("Build Your Own Model", "03-template/build-your-own-model.md"),
    ("Documentation Index", "index.md"),
]

LINK = re.compile(r"\]\(([^)\s]+)\)")
FRONTMATTER = re.compile(r"^---\n.*?\n---\n", re.S)


def absolute(target: str, page_rel: str) -> str:
    """Resolve one link target for a page at ``page_rel``."""
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return target
    path, has_fragment, fragment = target.partition("#")
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(page_rel), path))
    if resolved.startswith("..") or resolved in {"README.md", "fdo.json", "MODEL_TEMPLATE.md"}:
        url = f"{REPO}/blob/main/{resolved}"
    elif resolved.endswith(".md"):
        url = f"{SITE}/{resolved[:-3]}" if resolved != "index.md" else f"{SITE}/"
    else:
        url = f"{REPO}/blob/main/documentation/{resolved}"
    return url + (f"#{fragment}" if has_fragment else "")


def rewrite_links(text: str, page_rel: str) -> str:
    return LINK.sub(lambda match: f"]({absolute(match.group(1), page_rel)})", text)


def build_full() -> str:
    lines = [
        "# model__prediction__generic__null-model — full documentation",
        "",
        "> Complete inlined content of the documentation pages, for LLM context windows.",
        "",
    ]
    for title, rel in PAGES:
        text = FRONTMATTER.sub("", (ROOT / rel).read_text(), count=1).strip()
        lines += [f'<doc title="{title}" path="{rel}">', rewrite_links(text, rel), "</doc>", ""]
    return "\n".join(lines)


def build_public_index() -> str:
    text = (ROOT / "llms.txt").read_text()

    def replace(match: re.Match[str]) -> str:
        target = match.group(1)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return match.group(0)
        if target.startswith("../"):
            return f"]({REPO}/blob/main/{posixpath.normpath(target[3:])})"
        if target == "catalogue.json":
            return f"]({REPO}/blob/main/documentation/catalogue.json)"
        return match.group(0)

    return LINK.sub(replace, text)


def main() -> None:
    full = build_full()
    (ROOT / "llms-full.txt").write_text(full)
    (ROOT / "public" / "llms-full.txt").write_text(full)
    (ROOT / "public" / "llms.txt").write_text(build_public_index())
    print(f"llms-full: {len(full)} bytes")
    print("wrote public/llms.txt and public/llms-full.txt")


if __name__ == "__main__":
    main()
