"""권역/주제 정의·모델·선별 로직 (VENDORED).

이 파일은 형제 앱 korean_worldnews_dailybriefing 에서 그대로 복사한 것이다.
Source of truth:
  - REGIONS, TOPICS  ← briefing/config.py
  - Article, Classification ← briefing/models.py
  - select() ← briefing/render.py

형제 repo가 같은 머신에 있으면 tests/test_sync.py 가 이 사본이 원본과 동일한지
검증한다. 원본이 바뀌면 그 테스트가 실패하므로 여기서 맞춰 갱신한다.
"""

import re
from dataclasses import dataclass

# 표시 단계 중복 제거 임계값 (briefing/config.py DEDUP_SUMMARY_THRESHOLD 와 동일해야 함)
DEDUP_SUMMARY_THRESHOLD: float = 0.20

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
    section: str  # 국내=sid2, 해외=피드 slug
    origin: str = "domestic"  # "domestic"(네이버) | "foreign"(해외 RSS)


@dataclass(frozen=True, slots=True)
class Classification:
    id: str
    region: str
    topics: tuple[str, ...]
    score: int
    summary: str
    title_ko: str = ""  # 외국어 기사의 한국어 번역 제목(국내 기사는 빈 문자열)


Selection = dict[str, tuple[tuple[Article, Classification], ...]]


def _summary_tokens(article: Article, classification: Classification) -> frozenset[str]:
    """제목+요약을 정규화한 토큰 집합. 1글자 토큰은 제외."""
    cleaned = re.sub(r"[^\w\s]", " ", f"{article.title} {classification.summary}")
    return frozenset(word for word in cleaned.split() if len(word) > 1)


def _dedup_paraphrases(
    ranked: list[tuple[Article, Classification]], threshold: float
) -> list[tuple[Article, Classification]]:
    """점수 내림차순 목록에서 같은 사건(패러프레이즈) 중복을 제거한다."""
    kept: list[tuple[Article, Classification]] = []
    kept_tokens: list[frozenset[str]] = []
    for article, classification in ranked:
        tokens = _summary_tokens(article, classification)
        if any(
            tokens and kt and len(tokens & kt) / len(tokens | kt) >= threshold
            for kt in kept_tokens
        ):
            continue
        kept.append((article, classification))
        kept_tokens.append(tokens)
    return kept


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
        ranked = _dedup_paraphrases(ranked, DEDUP_SUMMARY_THRESHOLD)
        selection = {**selection, region: tuple(ranked[:top_n])}

    return selection
