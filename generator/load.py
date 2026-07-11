"""브리핑 JSON 디렉터리를 읽어 날짜별 (articles, classifications)로 파싱한다.

형제 앱 briefing/store.py 의 저장 형식을 미러한다:
  data/briefing_<YYYY-MM-DD>.json = {"day", "articles": [...], "classifications": [...]}
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from generator.core import Article, Classification

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DayData:
    day: str
    articles: tuple[Article, ...]
    classifications: tuple[Classification, ...]


def _parse_file(path: Path) -> DayData | None:
    """한 파일을 파싱한다. 손상·형식 이상이면 경고 후 None(빌드 중단 금지)."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        day = payload["day"]
        articles = tuple(
            Article(
                id=a["id"], title=a["title"], press=a["press"], lede=a["lede"],
                url=a["url"], date=a["date"], section=a["section"],
            )
            for a in payload["articles"]
        )
        classifications = tuple(
            Classification(
                id=c["id"], region=c["region"], topics=tuple(c["topics"]),
                score=int(c["score"]), summary=c["summary"],
            )
            for c in payload["classifications"]
        )
        return DayData(day=day, articles=articles, classifications=classifications)
    except (OSError, ValueError, KeyError, TypeError) as error:
        logger.warning("브리핑 파일 건너뜀 %s: %s", path.name, error)
        return None


def load_days(data_dir: Path) -> tuple[DayData, ...]:
    """data_dir 의 briefing_*.json 을 모두 읽어 날짜 내림차순(최신 먼저)으로 돌려준다."""
    paths = sorted(Path(data_dir).glob("briefing_*.json"), reverse=True)
    days = tuple(d for d in (_parse_file(p) for p in paths) if d is not None)
    logger.info("브리핑 %d일치 로드 (파일 %d개)", len(days), len(paths))
    return days
