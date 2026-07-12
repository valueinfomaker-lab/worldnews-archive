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

    site_url = config.SITE_URL
    common = {
        "site_title": config.SITE_TITLE,
        "site_full": config.SITE_FULL,
        "site_tagline": config.SITE_TAGLINE,
        "site_desc": config.SITE_DESC,
        "base_path": config.BASE_PATH,
        "subscribe_endpoint": config.SUBSCRIBE_ENDPOINT,
        "site_url": site_url,
        "kakao_openchat_url": config.KAKAO_OPENCHAT_URL,
        "jsonld": _jsonld(site_url),
        # 페이지별 오버라이드 기본값(인덱스가 사용).
        "og_title": f"{config.SITE_TITLE} — 세계뉴스 일일 브리핑",
        "og_url": site_url,
        "canonical_url": site_url,
        "page_description": config.SITE_DESC,
    }

    # contexts 는 최신 날짜가 먼저다. 이전날=더 과거(i+1), 다음날=더 최신(i-1).
    for i, ctx in enumerate(contexts):
        newer = contexts[i - 1]["day"] if i > 0 else None
        older = contexts[i + 1]["day"] if i + 1 < len(contexts) else None
        page_url = f"{site_url}{ctx['day']}.html"
        regions = list(ctx["region_counts"].keys())
        day_desc = (
            f"{ctx['day']} 세계뉴스 일일 브리핑 — {', '.join(regions[:6])} 등 {ctx['total']}건 요약."
            if regions
            else f"{ctx['day']} 세계뉴스 일일 브리핑."
        )
        html = day_template.render(
            **{**common,
               "og_title": f"{ctx['day']} 세계뉴스 브리핑 · {config.SITE_TITLE}",
               "og_url": page_url, "canonical_url": page_url, "page_description": day_desc},
            **ctx, topics=TOPICS, prev_day=older, next_day=newer,
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

    days = [c["day"] for c in contexts]
    (output_dir / "sitemap.xml").write_text(_sitemap(site_url, days), encoding="utf-8")
    (output_dir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {site_url}sitemap.xml\n", encoding="utf-8"
    )
    (output_dir / "404.html").write_text(_not_found_page(site_url), encoding="utf-8")

    logger.info("빌드 완료: %d일치 → %s", len(contexts), output_dir)
    return {"days": len(contexts), "output_dir": str(output_dir)}


def _jsonld(site_url: str) -> str:
    """사이트 공통 구조화 데이터(Organization + WebSite). 검색엔진 표현 개선."""
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": f"{site_url}#org",
                "name": config.SITE_TITLE,
                "alternateName": config.SITE_FULL,
                "url": site_url,
                "logo": f"{site_url}assets/icon.png",
            },
            {
                "@type": "WebSite",
                "@id": f"{site_url}#website",
                "name": config.SITE_TITLE,
                "url": site_url,
                "description": config.SITE_DESC,
                "inLanguage": "ko-KR",
                "publisher": {"@id": f"{site_url}#org"},
            },
        ],
    }
    return json.dumps(graph, ensure_ascii=False)


def _sitemap(site_url: str, days: list) -> str:
    """인덱스 + 모든 날짜 페이지의 sitemap.xml. lastmod 는 해당 날짜."""
    latest = days[0] if days else None
    urls = [(site_url, latest)] + [(f"{site_url}{d}.html", d) for d in days]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in urls:
        mod = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
        lines.append(f"  <url><loc>{loc}</loc>{mod}</url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def _not_found_page(site_url: str) -> str:
    """자체 완결형 브랜드 404(경로 무관하게 뜨므로 절대 URL만 사용)."""
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>페이지를 찾을 수 없습니다 · GRIP</title>"
        '<meta name="robots" content="noindex">'
        "<style>body{font-family:-apple-system,'Apple SD Gothic Neo',sans-serif;"
        "background:#0d2b49;color:#fff;margin:0;min-height:100vh;display:flex;"
        "align-items:center;justify-content:center;text-align:center}"
        ".wm{font-weight:800;font-size:30px;letter-spacing:-.02em}"
        ".wm i{color:#e6b25f;font-style:normal}"
        "p{color:#c7d8ec;font-size:15px;margin:14px 0 22px}"
        "a{display:inline-block;background:#fee500;color:#3c1e1e;text-decoration:none;"
        "font-weight:700;font-size:14px;padding:11px 20px;border-radius:8px}</style></head>"
        '<body><div><div class="wm">GR<i>I</i>P</div>'
        "<p>요청하신 페이지를 찾을 수 없습니다.</p>"
        f'<a href="{site_url}">홈으로 돌아가기</a></div></body></html>'
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    summary = build()
    print(f"빌드 완료: {summary['days']}일치 → {summary['output_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
