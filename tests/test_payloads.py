from generator.core import Article, Classification, select
from generator.payloads import (
    article_plain,
    day_html,
    day_plain,
    region_plain,
)


def _art(aid, title):
    return Article(id=aid, title=title, press="언론사", lede="요약",
                   url=f"https://n.news.naver.com/mnews/article/{aid}", date="20260711", section="231")


def _cls(aid, region, score):
    return Classification(id=aid, region=region, topics=("경제", "외교"), score=score, summary="요약")


def test_article_plain_is_title_score_then_url():
    a = _art("020/1", "테스트 제목")
    c = _cls("020/1", "아세안", 80)
    assert article_plain(a, c) == "테스트 제목 (80)\nhttps://n.news.naver.com/mnews/article/020/1"


def test_region_plain_has_bracket_header():
    a = _art("020/1", "제목")
    c = _cls("020/1", "중국", 70)
    text = region_plain("중국", ((a, c),))
    assert text.startswith("[중국]\n")
    assert "제목 (70)" in text and a.url in text


def test_day_plain_matches_render_plain_format():
    arts = (_art("020/1", "가"), _art("020/2", "나"))
    cls = (_cls("020/1", "아세안", 90), _cls("020/2", "중국", 60))
    sel = select(arts, cls)
    text = day_plain(sel, day="2026-07-11")
    assert text.startswith("세계뉴스 일일 브리핑 2026-07-11\n\n")
    assert "[아세안]" in text and "[중국]" in text
    assert "가 (90)" in text


def test_day_html_has_wrapper_and_escapes():
    a = _art("020/1", "<b>위험</b>")
    c = _cls("020/1", "아세안", 50)
    html = day_html(select((a,), (c,)), day="2026-07-11")
    assert html.startswith("<div style=")
    assert "총 1건" in html
    assert "&lt;b&gt;위험&lt;/b&gt;" in html  # 제목 이스케이프
