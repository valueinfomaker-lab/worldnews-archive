"""vendored 사본이 형제 앱 원본과 일치하는지 검증한다.

형제 repo(korean_worldnews_dailybriefing)가 같은 머신에 있고 import 가능하면
REGIONS/TOPICS/select/render_plain/render_html 을 원본과 대조한다.
없거나 import 불가하면 skip(예: CI). 원본이 바뀌면 여기서 실패해 드리프트를 알린다.
"""

import sys
from pathlib import Path

import pytest

SIBLING = Path("/Users/joseph/korean_worldnews_dailybriefing")


def _import_sibling():
    if not (SIBLING / "briefing").is_dir():
        pytest.skip("형제 repo 없음")
    if str(SIBLING) not in sys.path:
        sys.path.insert(0, str(SIBLING))
    try:
        from briefing import config as bconfig  # noqa: PLC0415
        from briefing import render as brender  # noqa: PLC0415
    except ImportError as error:
        pytest.skip(f"형제 repo import 불가: {error}")
    return bconfig, brender


def _sample():
    from generator.core import Article, Classification  # noqa: PLC0415

    arts = tuple(
        Article(id=f"020/{i}", title=f"제목{i}", press="언론사", lede="요약",
                url=f"https://n.news.naver.com/mnews/article/020/{i}", date="20260711", section="231")
        for i in range(3)
    )
    cls = (
        Classification(id="020/0", region="아세안", topics=("경제",), score=90, summary="가"),
        Classification(id="020/1", region="중국", topics=("외교",), score=60, summary="나"),
        Classification(id="020/2", region="해당없음", topics=("사회",), score=80, summary="다"),
    )
    return arts, cls


def test_regions_and_topics_match_sibling():
    bconfig, _ = _import_sibling()
    from generator.core import REGIONS, TOPICS  # noqa: PLC0415

    assert REGIONS == bconfig.REGIONS
    assert TOPICS == bconfig.TOPICS


def test_select_matches_sibling():
    _, brender = _import_sibling()
    from generator.core import select  # noqa: PLC0415

    arts, cls = _sample()
    mine = select(arts, cls)
    theirs = brender.select(arts, cls)
    assert list(mine) == list(theirs)
    assert {r: [c.id for _, c in p] for r, p in mine.items()} == {
        r: [c.id for _, c in p] for r, p in theirs.items()
    }


def test_day_payloads_match_sibling_render():
    _, brender = _import_sibling()
    from generator.core import select  # noqa: PLC0415
    from generator.payloads import day_html, day_plain  # noqa: PLC0415

    arts, cls = _sample()
    sel = select(arts, cls)
    assert day_plain(sel, day="2026-07-11") == brender.render_plain(sel, day="2026-07-11")
    assert day_html(sel, day="2026-07-11") == brender.render_html(sel, day="2026-07-11")
