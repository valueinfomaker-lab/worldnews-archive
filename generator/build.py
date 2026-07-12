"""정적 사이트 빌드 오케스트레이터. `python -m generator.build`.

기존 앱의 data/briefing_*.json 을 읽어 날짜별 페이지 + 인덱스를 docs/ 에 생성한다.
매 실행 전체 재빌드(idempotent).
"""

import json
import logging
import shutil

from jinja2 import Environment, FileSystemLoader, select_autoescape

from generator import config, payloads
from generator.core import REGIONS, TOPICS, select
from generator.load import DayData, load_days

logger = logging.getLogger(__name__)


def _safe_key(article_id: str) -> str:
    return "a" + article_id.replace("/", "_")


def _region_dicts(selection, embed: dict, *, foreign: bool, rprefix: str) -> list:
    """한 selection(국내 또는 해외)의 권역 목록 dict 를 만들고 embed 에 페이로드를 채운다.

    해외 항목은 대표 제목=title_ko(없으면 원제), orig=원문 제목(부제)로 준다.
    권역 페이로드 키는 rprefix 로 구분(국내 r0/r1…, 해외 fr0/fr1…). 기사 페이로드 키는
    id 해시라 국내·해외가 애초에 충돌하지 않는다.
    """
    regions = []
    for idx, (region, pairs) in enumerate(selection.items()):
        embed[f"pt-{rprefix}{idx}"] = payloads.region_plain(region, pairs, foreign=foreign)
        embed[f"ht-{rprefix}{idx}"] = payloads.region_html(region, pairs, foreign=foreign)
        articles = []
        for article, c in pairs:
            key = _safe_key(article.id)
            embed[f"pt-{key}"] = payloads.article_plain(article, c, foreign=foreign)
            embed[f"ht-{key}"] = payloads.article_html(article, c, foreign=foreign)
            articles.append({
                "title": (c.title_ko or article.title) if foreign else article.title,
                "orig": article.title if (foreign and c.title_ko and c.title_ko != article.title) else "",
                "url": article.url,
                "press": article.press,
                "topics": " · ".join(c.topics),
                "topics_list": list(c.topics),
                "score": c.score,
                "summary": c.summary,
                "key": key,
            })
        regions.append({"name": region, "idx": idx, "articles": articles})
    return regions


def _day_context(data: DayData) -> dict:
    """한 날짜 페이지에 필요한 컨텍스트 + 숨은 페이로드를 구성한다."""
    domestic = tuple(a for a in data.articles if a.origin == "domestic")
    overseas = tuple(a for a in data.articles if a.origin == "foreign")
    dsel = select(domestic, data.classifications, top_n=config.TOP_N)
    fsel = select(overseas, data.classifications, top_n=config.TOP_N)
    total = sum(len(p) for p in dsel.values()) + sum(len(p) for p in fsel.values())

    embed: dict[str, str] = {
        "pt-day": payloads.day_plain(dsel, day=data.day, foreign=fsel),
        "ht-day": payloads.day_html(dsel, day=data.day, foreign=fsel),
    }
    regions = _region_dicts(dsel, embed, foreign=False, rprefix="r")
    foreign_regions = _region_dicts(fsel, embed, foreign=True, rprefix="fr")

    region_counts = {
        region: len(dsel.get(region, ())) + len(fsel.get(region, ()))
        for region in REGIONS
        if dsel.get(region) or fsel.get(region)
    }
    return {
        "day": data.day,
        "total": total,
        "regions": regions,
        "foreign": foreign_regions,
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
    months = _group_by_month(index_entries)
    (output_dir / "index.html").write_text(
        index_template.render(**common, months=months, total_days=len(index_entries)),
        encoding="utf-8",
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


def _group_by_month(entries: list) -> list:
    """최신순 날짜 목록을 'YYYY-MM' 단위로 묶는다(월 내에서도 최신순 유지)."""
    from itertools import groupby

    groups = []
    for key, items in groupby(entries, key=lambda e: e["day"][:7]):
        year, month = key.split("-")
        groups.append({"key": key, "label": f"{year}년 {int(month)}월", "days": list(items)})
    return groups


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
