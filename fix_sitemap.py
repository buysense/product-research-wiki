#!/usr/bin/env python3
"""빌드된 sitemap.xml의 lastmod를 각 파일의 실제 git 커밋 날짜로 교체한다."""
import re
import subprocess
from pathlib import Path

SITE_URL = "https://buysense.app/"
SITE_DIR = Path("site")
DOCS_DIR = Path("docs")


def get_git_date(md_path: Path) -> str | None:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", str(md_path)],
        capture_output=True,
        text=True,
    )
    date = result.stdout.strip()
    return date if re.match(r"\d{4}-\d{2}-\d{2}", date) else None


def url_to_md(url: str) -> Path | None:
    rel = url.removeprefix(SITE_URL).rstrip("/")
    if not rel:
        return DOCS_DIR / "index.md"
    for candidate in (DOCS_DIR / f"{rel}.md", DOCS_DIR / rel / "index.md"):
        if candidate.exists():
            return candidate
    return None


def main():
    sitemap = SITE_DIR / "sitemap.xml"
    content = sitemap.read_text(encoding="utf-8")
    updated = fixed = 0

    def replace(m: re.Match) -> str:
        nonlocal updated, fixed
        updated += 1
        md = url_to_md(m.group(1))
        date = get_git_date(md) if md else None
        if date:
            fixed += 1
            return f"<loc>{m.group(1)}</loc>\n    <lastmod>{date}</lastmod>"
        return m.group(0)

    content = re.sub(
        r"<loc>([^<]+)</loc>\s*<lastmod>[^<]+</lastmod>", replace, content
    )
    sitemap.write_text(content, encoding="utf-8")
    print(f"sitemap: {updated} URLs processed, {fixed} lastmod dates updated")


if __name__ == "__main__":
    main()
