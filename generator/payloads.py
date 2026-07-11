"""복사 버튼용 평문·HTML 페이로드 생성.

형제 앱 briefing/render.py 의 render_plain / render_html 형식을 그대로 복제한다.
day 스코프 평문·HTML 은 이메일 본문과 바이트 동일해야 한다(tests/test_sync.py 로 검증).
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


# ---- 평문 (카톡용) --------------------------------------------------------

def article_plain(article: Article, c: Classification) -> str:
    return f"{article.title} ({c.score})\n{article.url}"


def region_plain(region: str, pairs: tuple[tuple[Article, Classification], ...]) -> str:
    lines = [f"[{region}]"]
    for article, c in pairs:
        lines += [f"{article.title} ({c.score})", article.url, ""]
    return "\n".join(lines).rstrip("\n")


def day_plain(selection: Selection, *, day: str) -> str:
    """render_plain 과 바이트 동일."""
    lines = [f"세계뉴스 일일 브리핑 {day}", ""]
    for region, pairs in selection.items():
        lines = [*lines, f"[{region}]"]
        for article, c in pairs:
            lines = [*lines, f"{article.title} ({c.score})", article.url, ""]
    return "\n".join(lines)


# ---- HTML (이메일 서식용) --------------------------------------------------

def article_html(article: Article, c: Classification) -> str:
    topics = " · ".join(escape(t) for t in c.topics)
    return (
        f'<div style="{_ITEM}">'
        f'<a href="{escape(article.url)}" style="{_TITLE_LINK}">{escape(article.title)}</a>'
        f'<div style="{_META}">{escape(article.press)} · {topics} · 추천 {c.score}</div>'
        f'<div style="{_SUMMARY}">{escape(c.summary)}</div>'
        f"</div>"
    )


def region_html(region: str, pairs: tuple[tuple[Article, Classification], ...]) -> str:
    parts = [f'<h2 style="{_REGION_HEADING}">{escape(region)}</h2>']
    parts += [article_html(a, c) for a, c in pairs]
    return "".join(parts)


def day_html(selection: Selection, *, day: str) -> str:
    """render_html 과 바이트 동일."""
    total = sum(len(pairs) for pairs in selection.values())
    parts = [
        f'<div style="{_WRAPPER}">',
        f'<h1 style="font-size:20px;margin:0 0 4px">세계뉴스 일일 브리핑</h1>',
        f'<div style="{_META}">{escape(day)} · 총 {total}건</div>',
    ]
    for region, pairs in selection.items():
        parts.append(f'<h2 style="{_REGION_HEADING}">{escape(region)}</h2>')
        for article, c in pairs:
            parts.append(article_html(article, c))
    if not selection:
        parts.append('<p style="color:#666">해당 권역 기사가 없습니다.</p>')
    parts.append("</div>")
    return "".join(parts)
