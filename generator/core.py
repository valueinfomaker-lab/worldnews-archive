"""권역/주제 정의·모델·선별 로직 (VENDORED).

이 파일은 형제 앱 korean_worldnews_dailybriefing 에서 그대로 복사한 것이다.
Source of truth:
  - REGIONS, TOPICS  ← briefing/config.py
  - Article, Classification ← briefing/models.py
  - select() ← briefing/render.py

형제 repo가 같은 머신에 있으면 tests/test_sync.py 가 이 사본이 원본과 동일한지
검증한다. 원본이 바뀌면 그 테스트가 실패하므로 여기서 맞춰 갱신한다.
"""

from dataclasses import dataclass

REGIONS: tuple[str, ...] = (
    "아세안",
    "인도·남아시아",
    "아프리카·중동",
    "중·동부유럽",
    "러시아·유라시아",
    "중남미",
    "중국",
    "선진국",
    "해당없음",
)

TOPICS: tuple[str, ...] = (
    "경제",
    "정책",
    "외교",
    "안보",
    "정치",
    "환경",
    "보건",
    "사회",
)


@dataclass(frozen=True, slots=True)
class Article:
    id: str
    title: str
    press: str
    lede: str
    url: str
    date: str
    section: str


@dataclass(frozen=True, slots=True)
class Classification:
    id: str
    region: str
    topics: tuple[str, ...]
    score: int
    summary: str


Selection = dict[str, tuple[tuple[Article, Classification], ...]]


def select(
    articles: tuple[Article, ...],
    classifications: tuple[Classification, ...],
    *,
    top_n: int = 5,
    min_score: int = 0,
    topics: tuple[str, ...] | None = None,
) -> Selection:
    """권역별로 추천점수 내림차순 상위 `top_n`건을 고른다. `해당없음`은 제외."""
    by_id = {a.id: a for a in articles}
    selection: Selection = {}

    for region in REGIONS:
        if region == "해당없음":
            continue
        matched = [
            (by_id[c.id], c)
            for c in classifications
            if c.region == region
            and c.id in by_id
            and c.score >= min_score
            and (topics is None or any(t in topics for t in c.topics))
        ]
        if not matched:
            continue
        ranked = sorted(matched, key=lambda pair: pair[1].score, reverse=True)
        selection = {**selection, region: tuple(ranked[:top_n])}

    return selection
