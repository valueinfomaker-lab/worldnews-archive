"""정적 사이트 빌드 오케스트레이터. `python -m generator.build`.

기존 앱의 data/briefing_*.json 을 읽어 날짜별 페이지 + 인덱스를 docs/ 에 생성한다.
매 실행 전체 재빌드(idempotent).
"""

import json
import logging
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape

from generator import config, payloads
from generator.core import TOPICS, select
from generator.load import DayData, load_days

logger = logging.getLogger(__name__)


def _safe_key(article_id: str) -> str:
    return "a" + article_id.replace("/", "_")


def _day_context(data: DayData) -> dict:
    """한 날짜 페이지에 필요한 컨텍스트 + 숨은 페이로드를 구성한다."""
    selection = select(data.articles, data.classifications, top_n=config.TOP_N)
    total = sum(len(pairs) for pairs in selection.values())

    embed: dict[str, str] = {
        "pt-day": payloads.day_plain(selection, day=data.day),
        "ht-day": payloads.day_html(selection, day=data.day),
    }
    regions = []
    for idx, (region, pairs) in enumerate(selection.items()):
        embed[f"pt-r{idx}"] = payloads.region_plain(region, pairs)
        embed[f"ht-r{idx}"] = payloads.region_html(region, pairs)
        articles = []
        for article, c in pairs:
            key = _safe_key(article.id)
            embed[f"pt-{key}"] = payloads.article_plain(article, c)
            embed[f"ht-{key}"] = payloads.article_html(article, c)
            articles.append({
                "title": article.title,
                "url": article.url,
                "press": article.press,
                "topics": " · ".join(c.topics),
                "topics_list": list(c.topics),
                "score": c.score,
                "summary": c.summary,
                "key": key,
            })
        regions.append({"name": region, "idx": idx, "articles": articles})

    region_counts = {region: len(pairs) for region, pairs in selection.items()}
    return {
        "day": data.day,
        "total": total,
        "regions": regions,
        "embed": embed,
        "region_counts": region_counts,
    }


def build(*, data_dir=None, output_dir=None) -> dict:
    """전체 빌드. 생성 요약(dict)을 돌려준다."""
    data_dir = data_dir or config.DATA_DIR
    output_dir = output_dir or config.OUTPUT_DIR

    env = Environment(
        loader=FileSystemLoader(str(config.TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )
    day_template = env.get_template("day.html.j2")
    index_template = env.get_template("index.html.j2")

    days = load_days(data_dir)
    contexts = [_day_context(d) for d in days]

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")

    # 에셋 복사
    assets_out = output_dir / "assets"
    assets_out.mkdir(exist_ok=True)
    for asset in config.ASSETS_DIR.iterdir():
        if asset.is_file():
            shutil.copy2(asset, assets_out / asset.name)

    common = {"site_title": config.SITE_TITLE, "base_path": config.BASE_PATH}

    # contexts 는 최신 날짜가 먼저다. 이전날=더 과거(i+1), 다음날=더 최신(i-1).
    for i, ctx in enumerate(contexts):
        newer = contexts[i - 1]["day"] if i > 0 else None
        older = contexts[i + 1]["day"] if i + 1 < len(contexts) else None
        html = day_template.render(
            **common, **ctx, topics=TOPICS, prev_day=older, next_day=newer
        )
        (output_dir / f"{ctx['day']}.html").write_text(html, encoding="utf-8")

    index_entries = [
        {"day": c["day"], "total": c["total"], "regions": c["region_counts"]}
        for c in contexts
    ]
    (output_dir / "index.html").write_text(
        index_template.render(**common, days=index_entries), encoding="utf-8"
    )
    (output_dir / "dates.json").write_text(
        json.dumps(index_entries, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    logger.info("빌드 완료: %d일치 → %s", len(contexts), output_dir)
    return {"days": len(contexts), "output_dir": str(output_dir)}


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    summary = build()
    print(f"빌드 완료: {summary['days']}일치 → {summary['output_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
