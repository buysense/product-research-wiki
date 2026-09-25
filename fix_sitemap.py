#!/usr/bin/env python3
"""빌드된 sitemap.xml의 lastmod를 문서가 선언한 `contentUpdated`로 교체한다.

MkDocs 기본 lastmod는 빌드 시각이라 657개 URL이 매 배포마다 "오늘 바뀜"이 된다.
Google은 lastmod가 실제 변경을 반영하지 않으면 무시하므로, 무엇이 유의미한 변경인지
문서 자신이 front matter `contentUpdated`로 들고 있게 한다. 워커가 신규 발행·포맷
변경에서만 이 값을 새기고, 가격·리뷰수 patch는 건드리지 않는다.

폴백은 git 최종 커밋일이다. 가격 배치가 매일 전 문서를 만지므로 이 값은 사실상
빌드일과 같다. 즉 폴백은 "정직한 날짜"가 아니라 예전 동작일 뿐이며, 폴백으로 세는
URL이 늘어나면 백필이 빠졌다는 신호다. 그래서 두 경로를 나눠 센다.
"""
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

SITE_URL = "https://buysense.app/"
SITE_DIR = Path("site")
DOCS_DIR = Path("docs")

# 첫 --- 블록만 front matter로 본다. 657개 중 445개가 CRLF라 \r을 함께 받는다.
FRONT_MATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
CONTENT_UPDATED = re.compile(r"^contentUpdated:[^\S\r\n]*(\S+)[^\S\r\n]*$", re.MULTILINE)
DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def get_content_updated(md_path: Path) -> str | None:
    front = FRONT_MATTER.match(md_path.read_text(encoding="utf-8"))
    if not front:
        return None
    found = CONTENT_UPDATED.search(front.group(1))
    if not found:
        return None
    value = found.group(1)
    return value if DATE.match(value) else None


def get_git_date(md_path: Path) -> str | None:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cs", "--", str(md_path)],
        capture_output=True,
        text=True,
    )
    date = result.stdout.strip()
    return date if DATE.match(date) else None


def url_to_md(url: str) -> Path | None:
    # sitemap의 loc은 퍼센트 인코딩돼 있다. 한글 slug 70개가 여기서 디코딩되지 않으면
    # 파일을 못 찾아 lastmod가 교정되지 않은 채 빌드 시각으로 남는다.
    rel = unquote(url.removeprefix(SITE_URL)).rstrip("/")
    if not rel:
        return DOCS_DIR / "index.md"
    for candidate in (DOCS_DIR / f"{rel}.md", DOCS_DIR / rel / "index.md"):
        if candidate.exists():
            return candidate
    return None


def main():
    sitemap = SITE_DIR / "sitemap.xml"
    content = sitemap.read_text(encoding="utf-8")
    processed = declared = from_git = unresolved = 0

    def replace(m: re.Match) -> str:
        nonlocal processed, declared, from_git, unresolved
        processed += 1
        md = url_to_md(m.group(1))
        date = get_content_updated(md) if md else None
        if date:
            declared += 1
        else:
            date = get_git_date(md) if md else None
            if date:
                from_git += 1
        if not date:
            # 날짜를 지어내지 않는다. MkDocs 기본값을 그대로 두고 카운트에만 남긴다.
            unresolved += 1
            return m.group(0)
        return f"<loc>{m.group(1)}</loc>\n    <lastmod>{date}</lastmod>"

    content = re.sub(
        r"<loc>([^<]+)</loc>\s*<lastmod>[^<]+</lastmod>", replace, content
    )
    sitemap.write_text(content, encoding="utf-8")
    print(
        f"sitemap: {processed} URLs / contentUpdated {declared} / git 폴백 {from_git} "
        f"/ 미해결 {unresolved}"
    )


if __name__ == "__main__":
    main()
