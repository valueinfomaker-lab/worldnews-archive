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


def _region_dicts(selection, embed: dict, *, foreign: bool) -> list:
    """한 카테고리(국내 또는 해외) selection 의 권역 목록 dict 를 만들고 embed 를 채운다.

    해외 항목은 대표 제목=title_ko(없으면 원제), orig=원문 제목(부제)로 준다.
    국내·해외는 서로 다른 페이지로 나뉘어 embed 가 분리되므로 권역 키는 r{idx} 로 공통.
    기사 페이로드 키(id 해시)는 국내·해외가 애초에 충돌하지 않는다.
    """
    regions = []
    for idx, (region, pairs) in enumerate(selection.items()):
        embed[f"pt-r{idx}"] = payloads.region_plain(region, pairs, foreign=foreign)
        embed[f"ht-r{idx}"] = payloads.region_html(region, pairs, foreign=foreign)
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


def _split(data: DayData):
    """한 날짜를 (국내 selection, 해외 selection)로 나눈다."""
    domestic = tuple(a for a in data.articles if a.origin == "domestic")
    overseas = tuple(a for a in data.articles if a.origin == "foreign")
    dsel = select(domestic, data.classifications, top_n=config.TOP_N)
    fsel = select(overseas, data.classifications, top_n=config.TOP_N)
    return dsel, fsel


def _page_embed(day: str, selection, *, foreign: bool) -> tuple[dict, list]:
    """한 카테고리 페이지의 embed(숨은 페이로드) + 권역 목록을 만든다."""
    if foreign:
        embed: dict[str, str] = {
            "pt-day": payloads.day_plain({}, day=day, foreign=selection),
            "ht-day": payloads.day_html({}, day=day, foreign=selection),
        }
    else:
        embed = {
            "pt-day": payloads.day_plain(selection, day=day),
            "ht-day": payloads.day_html(selection, day=day),
        }
    regions = _region_dicts(selection, embed, foreign=foreign)
    return embed, regions


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
    infos = [{"day": d.day, "sels": _split(d)} for d in days]  # sels=(dsel, fsel)

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

    # 카테고리별 날짜 순서(최신 먼저). 국내는 모든 날짜, 해외는 해외 기사가 있는 날짜만.
    domestic_days = [x["day"] for x in infos]
    foreign_days = [x["day"] for x in infos if x["sels"][1]]

    def _render(day: str, selection, *, foreign: bool, has_foreign: bool, ordered: list) -> None:
        embed, regions = _page_embed(day, selection, foreign=foreign)
        total = sum(len(p) for p in selection.values())
        suffix = "-foreign" if foreign else ""
        cat_label = "해외 언론 브리핑" if foreign else "국내 언론 브리핑"
        i = ordered.index(day)
        newer = ordered[i - 1] if i > 0 else None
        older = ordered[i + 1] if i + 1 < len(ordered) else None
        page_url = f"{site_url}{day}{suffix}.html"
        names = [r["name"] for r in regions]
        desc = (
            f"{day} {cat_label} — {', '.join(names[:6])} 등 {total}건 요약."
            if names else f"{day} {cat_label} (기사 없음)."
        )
        html = day_template.render(
            **{**common,
               "og_title": f"{day} {cat_label} · {config.SITE_TITLE}",
               "og_url": page_url, "canonical_url": page_url, "page_description": desc},
            day=day, total=total, regions=regions, embed=embed, topics=TOPICS,
            is_foreign=foreign, category_sub=cat_label, has_foreign=has_foreign,
            page_suffix=suffix, prev_day=older, next_day=newer,
        )
        (output_dir / f"{day}{suffix}.html").write_text(html, encoding="utf-8")

    for x in infos:
        dsel, fsel = x["sels"]
        has_foreign = bool(fsel)
        _render(x["day"], dsel, foreign=False, has_foreign=has_foreign, ordered=domestic_days)
        if has_foreign:
            _render(x["day"], fsel, foreign=True, has_foreign=True, ordered=foreign_days)

    index_entries = []
    for x in infos:
        dsel, fsel = x["sels"]
        combined = {
            r: len(dsel.get(r, ())) + len(fsel.get(r, ()))
            for r in REGIONS if dsel.get(r) or fsel.get(r)
        }
        index_entries.append({
            "day": x["day"],
            "dom_total": sum(len(p) for p in dsel.values()),
            "for_total": sum(len(p) for p in fsel.values()),
            "has_foreign": bool(fsel),
            "regions": combined,
        })
    months = _group_by_month(index_entries)
    (output_dir / "index.html").write_text(
        index_template.render(**common, months=months, total_days=len(index_entries)),
        encoding="utf-8",
    )
    (output_dir / "dates.json").write_text(
        json.dumps(index_entries, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    (output_dir / "sitemap.xml").write_text(
        _sitemap(site_url, domestic_days, foreign_days), encoding="utf-8"
    )
    (output_dir / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {site_url}sitemap.xml\n", encoding="utf-8"
    )
    (output_dir / "404.html").write_text(_not_found_page(site_url), encoding="utf-8")

    logger.info(
        "빌드 완료: 국내 %d일 + 해외 %d일 → %s",
        len(domestic_days), len(foreign_days), output_dir,
    )
    return {"days": len(infos), "foreign_days": len(foreign_days), "output_dir": str(output_dir)}


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


def _sitemap(site_url: str, domestic_days: list, foreign_days: list) -> str:
    """인덱스 + 국내/해외 날짜 페이지의 sitemap.xml. lastmod 는 해당 날짜."""
    latest = domestic_days[0] if domestic_days else None
    urls = (
        [(site_url, latest)]
        + [(f"{site_url}{d}.html", d) for d in domestic_days]
        + [(f"{site_url}{d}-foreign.html", d) for d in foreign_days]
    )
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
