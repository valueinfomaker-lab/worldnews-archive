from generator.core import REGIONS, TOPICS, Article, Classification, select


def _article(aid, title="제목", score_url="x"):
    return Article(
        id=aid, title=title, press="언론사", lede="요약",
        url=f"https://n.news.naver.com/mnews/article/{aid}", date="20260711", section="231",
    )


def _cls(aid, region, score, topics=("경제",)):
    return Classification(id=aid, region=region, topics=topics, score=score, summary="한 줄")


def test_regions_and_topics_shape():
    assert REGIONS[-1] == "해당없음"
    assert len(REGIONS) == 9
    assert len(TOPICS) == 8


def test_select_excludes_none_region():
    arts = (_article("020/1"),)
    cls = (_cls("020/1", "해당없음", 90),)
    assert select(arts, cls) == {}


def test_select_orders_by_region_then_score_desc():
    arts = tuple(_article(f"020/{i}") for i in range(4))
    cls = (
        _cls("020/0", "선진국", 30),
        _cls("020/1", "아세안", 40),
        _cls("020/2", "아세안", 80),
        _cls("020/3", "중국", 50),
    )
    result = select(arts, cls)
    # 권역은 REGIONS 순서(아세안 < 중국 < 선진국)
    assert list(result) == ["아세안", "중국", "선진국"]
    # 아세안 내부는 점수 내림차순
    assert [c.score for _, c in result["아세안"]] == [80, 40]


def test_select_respects_top_n_min_score_and_topics():
    arts = tuple(_article(f"020/{i}") for i in range(3))
    cls = (
        _cls("020/0", "아세안", 90, topics=("경제",)),
        _cls("020/1", "아세안", 10, topics=("사회",)),
        _cls("020/2", "아세안", 70, topics=("외교",)),
    )
    # min_score=50 → 10점 제외
    assert len(select(arts, cls, min_score=50)["아세안"]) == 2
    # top_n=1 → 최고점 1건
    assert len(select(arts, cls, top_n=1)["아세안"]) == 1
    # topics 필터
    assert len(select(arts, cls, topics=("경제",))["아세안"]) == 1
