#!/usr/bin/env python3
"""Rebuild the LLM indexes after editing or regenerating the documentation.

Generates:
  documentation/llms-full.txt
  documentation/public/llms-full.txt   (served at /llms-full.txt)
  documentation/public/llms.txt        (served at /llms.txt)

Relative links are rewritten to absolute site URLs for pages, and to GitHub
blob URLs for repository files, so the served copies do not contain broken
`../` paths.

The repository and branch come from catalogue.json (`source.repo` and
`source.branch`); the site URL is derived from the repository. Override them
with REPO_URL, BRANCH and DOCS_SITE for a custom domain or a different remote.
Pages are discovered from catalogue.json, with a filesystem fallback for pages
that are not listed yet.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # documentation/
CATALOGUE = ROOT / "catalogue.json"
FALLBACK_REPO = "https://github.com/The-EPISERVE-Consortium/model__prediction__generic__null-model"
FALLBACK_SITE = "https://the-episerve-consortium.github.io/model__prediction__generic__null-model"

LINK = re.compile(r"\]\(([^)\s]+)\)")
FRONTMATTER = re.compile(r"^---\n.*?\n---\n", re.S)
SKIP_FILES = {"AGENTS.md", "CLAUDE.md", "_how-to-update.md"}


def git_remote() -> str | None:
    """Return the origin remote as a GitHub HTTPS URL, when possible."""
    try:
        remote = subprocess.check_output(
            ["git", "-C", str(ROOT.parent), "remote", "get-url", "origin"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None

    if remote.startswith("git@github.com:"):
        path = remote[len("git@github.com:") :]
    elif remote.startswith("ssh://git@github.com/"):
        path = remote[len("ssh://git@github.com/") :]
    elif remote.startswith("https://github.com/"):
        path = remote[len("https://github.com/") :]
    else:
        return None
    return f"https://github.com/{path.removesuffix('.git').rstrip('/')}"


def catalogue_data() -> dict:
    """Return catalogue.json as a dict, or an empty dict when missing."""
    if not CATALOGUE.exists():
        return {}
    data = json.loads(CATALOGUE.read_text())
    return data if isinstance(data, dict) else {}


def catalogue_source() -> dict:
    """Return the `source` block from catalogue.json, if present."""
    source = catalogue_data().get("source", {})
    return source if isinstance(source, dict) else {}


def default_repo() -> str:
    source = catalogue_source()
    return (os.environ.get("REPO_URL") or source.get("repo") or git_remote() or FALLBACK_REPO).rstrip("/")


def default_site(repo: str) -> str:
    override = os.environ.get("DOCS_SITE")
    if override:
        return override.rstrip("/")
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)$", repo)
    if match:
        owner, name = match.group(1).lower(), match.group(2)
        return f"https://{owner}.github.io/{name}"
    return FALLBACK_SITE


REPO = default_repo()
SITE = default_site(REPO)
BRANCH = os.environ.get("BRANCH") or catalogue_source().get("branch") or "main"
TITLE = catalogue_data().get("title") or "Documentation"


def discover_pages() -> list[tuple[str, str]]:
    """Return (title, path) pairs in the order they should be inlined."""
    pages: list[tuple[str, str]] = []

    def add(item: dict) -> None:
        path = item.get("path", "")
        if path.endswith(".md"):
            pages.append((item.get("title") or Path(path).stem.replace("-", " ").title(), path))
        for child in item.get("children", []):
            add(child)

    if CATALOGUE.exists():
        catalogue = catalogue_data()
        for item in catalogue.get("onboarding", []):
            add(item)
        for section in catalogue.get("sections", []):
            add(section)

    known = {path for _, path in pages}
    for file in sorted(ROOT.rglob("*.md")):
        relative = file.relative_to(ROOT).as_posix()
        if relative in known or file.name in SKIP_FILES:
            continue
        if any(part in {"node_modules", ".vitepress"} for part in file.parts):
            continue
        title = "Documentation Index" if relative == "index.md" else file.stem.replace("-", " ").title()
        pages.append((title, relative))

    # Keep the landing page last, and drop duplicates.
    pages.sort(key=lambda item: item[1] == "index.md")
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for title, path in pages:
        if path not in seen:
            seen.add(path)
            unique.append((title, path))
    return unique


PAGES = discover_pages()


def absolute(target: str, page_rel: str) -> str:
    """Resolve one link target for a page at ``page_rel``."""
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return target
    path, has_fragment, fragment = target.partition("#")
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(page_rel), path))
    repo_path = resolved.startswith("../")
    while resolved.startswith("../"):
        resolved = resolved[3:]
    if repo_path or resolved in {"README.md", "fdo.json", "MODEL_TEMPLATE.md"}:
        url = f"{REPO}/blob/{BRANCH}/{resolved}"
    elif resolved.endswith(".md"):
        url = f"{SITE}/{resolved[:-3]}" if resolved != "index.md" else f"{SITE}/"
    else:
        url = f"{REPO}/blob/{BRANCH}/documentation/{resolved}"
    return url + (f"#{fragment}" if has_fragment else "")


def rewrite_links(text: str, page_rel: str) -> str:
    return LINK.sub(lambda match: f"]({absolute(match.group(1), page_rel)})", text)


def build_full() -> str:
    lines = [
        f"# {TITLE} — full documentation",
        "",
        "> Complete inlined content of the documentation pages, for LLM context windows.",
        "",
    ]
    for title, rel in PAGES:
        text = FRONTMATTER.sub("", (ROOT / rel).read_text(), count=1).strip()
        lines += [f'<doc title="{title}" path="{rel}">', rewrite_links(text, rel), "</doc>", ""]
    return "\n".join(lines)


def build_public_index() -> str:
    """Rewrite llms.txt for serving from the site root."""
    return rewrite_links((ROOT / "llms.txt").read_text(), "llms.txt")


def main() -> None:
    full = build_full()
    (ROOT / "llms-full.txt").write_text(full)
    (ROOT / "public" / "llms-full.txt").write_text(full)
    (ROOT / "public" / "llms.txt").write_text(build_public_index())
    print(f"repo: {REPO}")
    print(f"site: {SITE}")
    print(f"pages: {len(PAGES)}")
    print(f"llms-full: {len(full)} bytes")


if __name__ == "__main__":
    main()
