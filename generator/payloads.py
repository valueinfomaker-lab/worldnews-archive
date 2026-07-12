"""복사 버튼용 평문·HTML 페이로드 생성.

형제 앱 briefing/render.py 의 render_plain / render_html 형식을 그대로 복제한다.
day 스코프 평문·HTML 은 이메일 본문과 바이트 동일해야 한다(tests/test_sync.py 로 검증).
해외(origin=foreign) 항목은 한국어 번역 제목(title_ko)을 대표로, 원문 제목을 부제로 쓴다.
스타일 상수도 render.py 에서 vendor.
"""

from html import escape

from generator.core import Article, Classification, Selection

_WRAPPER = (
    'font-family:-apple-system,"Apple SD Gothic Neo",sans-serif;'
    "max-width:680px;margin:0 auto;color:#1a1a1a;line-height:1.6"
)
_REGION_HEADING = (
    "font-size:17px;font-weight:700;margin:28px 0 10px;"
    "padding-bottom:6px;border-bottom:2px solid #1a5490;color:#1a5490"
)
_ITEM = "margin:0 0 14px;padding:0"
_TITLE_LINK = "color:#1a1a1a;text-decoration:none;font-weight:600;font-size:15px"
_META = "color:#666;font-size:12px;margin-top:2px"
_SUMMARY = "color:#444;font-size:13px;margin-top:3px"
_ORIG = "color:#888;font-size:12px;margin-top:1px"  # 해외 기사 원문 제목(부제)
_SECTION = (  # 해외 언론 구분 헤더
    "font-size:18px;font-weight:800;margin:34px 0 8px;padding-top:16px;"
    "border-top:2px solid #e5e7eb;color:#1a5490"
)


def _title(article: Article, c: Classification, *, foreign: bool) -> str:
    return (c.title_ko or article.title) if foreign else article.title


# ---- 평문 (카톡용) --------------------------------------------------------

def article_plain(article: Article, c: Classification, *, foreign: bool = False) -> str:
    return f"{_title(article, c, foreign=foreign)}\n{article.url}"


def region_plain(
    region: str, pairs: tuple[tuple[Article, Classification], ...], *, foreign: bool = False
) -> str:
    lines = [f"[{region}]"]
    for article, c in pairs:
        lines += [_title(article, c, foreign=foreign), article.url, ""]
    return "\n".join(lines).rstrip("\n")


def _plain_region_lines(selection: Selection, *, foreign: bool) -> list[str]:
    lines: list[str] = []
    for region, pairs in selection.items():
        lines.append(f"[{region}]")
        for article, c in pairs:
            lines += [_title(article, c, foreign=foreign), article.url, ""]
    return lines


def day_plain(selection: Selection, *, day: str, foreign: Selection | None = None) -> str:
    """render_plain 과 바이트 동일(해외 포함)."""
    lines = [f"세계뉴스 일일 브리핑 {day}", ""]
    lines += _plain_region_lines(selection, foreign=False)
    if foreign:
        lines += ["=== 해외 언론 브리핑 ===", ""]
        lines += _plain_region_lines(foreign, foreign=True)
    return "\n".join(lines)


# ---- HTML (이메일 서식용) --------------------------------------------------

def article_html(article: Article, c: Classification, *, foreign: bool = False) -> str:
    topics = " · ".join(escape(t) for t in c.topics)
    title = _title(article, c, foreign=foreign)
    orig = (
        f'<div style="{_ORIG}">{escape(article.title)}</div>'
        if foreign and c.title_ko and c.title_ko != article.title
        else ""
    )
    return (
        f'<div style="{_ITEM}">'
        f'<a href="{escape(article.url)}" style="{_TITLE_LINK}">{escape(title)}</a>'
        f"{orig}"
        f'<div style="{_META}">{escape(article.press)} · {topics}</div>'
        f'<div style="{_SUMMARY}">{escape(c.summary)}</div>'
        f"</div>"
    )


def region_html(
    region: str, pairs: tuple[tuple[Article, Classification], ...], *, foreign: bool = False
) -> str:
    parts = [f'<h2 style="{_REGION_HEADING}">{escape(region)}</h2>']
    parts += [article_html(a, c, foreign=foreign) for a, c in pairs]
    return "".join(parts)


def day_html(selection: Selection, *, day: str, foreign: Selection | None = None) -> str:
    """render_html 과 바이트 동일(해외 포함)."""
    foreign = foreign or {}
    total = sum(len(p) for p in selection.values()) + sum(len(p) for p in foreign.values())
    parts = [
        f'<div style="{_WRAPPER}">',
        f'<h1 style="font-size:20px;margin:0 0 4px">세계뉴스 일일 브리핑</h1>',
        f'<div style="{_META}">{escape(day)} · 총 {total}건</div>',
    ]
    for region, pairs in selection.items():
        parts.append(region_html(region, pairs, foreign=False))
    if foreign:
        parts.append(f'<h2 style="{_SECTION}">🌍 해외 언론 브리핑</h2>')
        for region, pairs in foreign.items():
            parts.append(region_html(region, pairs, foreign=True))
    if not selection and not foreign:
        parts.append('<p style="color:#666">해당 권역 기사가 없습니다.</p>')
    parts.append("</div>")
    return "".join(parts)
