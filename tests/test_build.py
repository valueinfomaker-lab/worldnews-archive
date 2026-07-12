import json

from generator.build import build


def _write_day(data_dir, day, articles, classifications):
    (data_dir / f"briefing_{day}.json").write_text(
        json.dumps({"day": day, "articles": articles, "classifications": classifications}, ensure_ascii=False),
        encoding="utf-8",
    )


def _art(aid, title):
    return {"id": aid, "title": title, "press": "언론사", "lede": "요약",
            "url": f"https://n.news.naver.com/mnews/article/{aid}", "date": "20260711", "section": "231"}


def _cls(aid, region, score=70):
    return {"id": aid, "region": region, "topics": ["경제"], "score": score, "summary": "요약"}


def test_build_emits_expected_files(tmp_path):
    data_dir = tmp_path / "data"
    out_dir = tmp_path / "docs"
    data_dir.mkdir()
    _write_day(data_dir, "2026-07-11",
               [_art("020/1", "가"), _art("020/2", "나")],
               [_cls("020/1", "아세안"), _cls("020/2", "중국")])
    _write_day(data_dir, "2026-07-10", [_art("020/3", "다")], [_cls("020/3", "선진국")])

    summary = build(data_dir=data_dir, output_dir=out_dir)

    assert summary["days"] == 2
    assert (out_dir / "index.html").exists()
    assert (out_dir / "2026-07-11.html").exists()
    assert (out_dir / "2026-07-10.html").exists()
    assert (out_dir / ".nojekyll").exists()
    assert (out_dir / "assets" / "style.css").exists()
    assert (out_dir / "assets" / "copy.js").exists()

    manifest = json.loads((out_dir / "dates.json").read_text(encoding="utf-8"))
    assert [d["day"] for d in manifest] == ["2026-07-11", "2026-07-10"]  # 최신 먼저

    page = (out_dir / "2026-07-11.html").read_text(encoding="utf-8")
    assert 'id="pt-day"' in page and 'id="ht-day"' in page       # 일 단위 페이로드
    assert 'id="pt-r0"' in page                                  # 권역 페이로드
    assert 'id="pt-a020_1"' in page                              # 기사 페이로드(안전 키)
    assert 'data-copy="rich"' in page and 'data-copy="plain"' in page
    assert "아세안" in page and "중국" in page


def test_build_index_has_subscribe_form(tmp_path, monkeypatch):
    from generator import config

    monkeypatch.setattr(config, "SUBSCRIBE_ENDPOINT", "https://script.example/exec")
    data_dir = tmp_path / "data"
    out_dir = tmp_path / "docs"
    data_dir.mkdir()
    _write_day(data_dir, "2026-07-11", [_art("020/1", "가")], [_cls("020/1", "아세안")])
    build(data_dir=data_dir, output_dir=out_dir)

    index = (out_dir / "index.html").read_text(encoding="utf-8")
    assert 'id="subscribe-form"' in index
    assert 'data-endpoint="https://script.example/exec"' in index
    assert 'id="sub-name"' in index and 'id="sub-email"' in index
    assert (out_dir / "assets" / "subscribe.js").exists()


def test_build_emits_og_tags_and_image(tmp_path):
    data_dir = tmp_path / "data"
    out_dir = tmp_path / "docs"
    data_dir.mkdir()
    _write_day(data_dir, "2026-07-11", [_art("020/1", "가")], [_cls("020/1", "아세안")])
    build(data_dir=data_dir, output_dir=out_dir)

    for page in ("index.html", "2026-07-11.html"):
        html = (out_dir / page).read_text(encoding="utf-8")
        assert 'property="og:image"' in html
        assert "assets/og-image.png" in html
        assert 'name="twitter:card" content="summary_large_image"' in html
        assert 'property="og:title"' in html
    assert (out_dir / "assets" / "og-image.png").exists()


def test_build_index_has_kakao_openchat_button(tmp_path, monkeypatch):
    from generator import config

    monkeypatch.setattr(config, "KAKAO_OPENCHAT_URL", "https://open.kakao.com/o/testABC")
    data_dir = tmp_path / "data"
    out_dir = tmp_path / "docs"
    data_dir.mkdir()
    _write_day(data_dir, "2026-07-11", [_art("020/1", "가")], [_cls("020/1", "아세안")])
    build(data_dir=data_dir, output_dir=out_dir)

    index = (out_dir / "index.html").read_text(encoding="utf-8")
    assert 'href="https://open.kakao.com/o/testABC"' in index
    assert "카카오톡 오픈채팅" in index


def test_build_emits_seo_files_and_per_page_canonical(tmp_path):
    data_dir = tmp_path / "data"
    out_dir = tmp_path / "docs"
    data_dir.mkdir()
    _write_day(data_dir, "2026-07-11", [_art("020/1", "가")], [_cls("020/1", "아세안")])
    build(data_dir=data_dir, output_dir=out_dir)

    assert (out_dir / "robots.txt").exists()
    assert (out_dir / "404.html").exists()
    sitemap = (out_dir / "sitemap.xml").read_text(encoding="utf-8")
    assert "<urlset" in sitemap and "2026-07-11.html" in sitemap

    # 날짜 페이지는 자기 URL로 canonical/og:url, 인덱스는 루트
    day = (out_dir / "2026-07-11.html").read_text(encoding="utf-8")
    assert 'rel="canonical" href="https://valueinfomaker-lab.github.io/worldnews-archive/2026-07-11.html"' in day
    assert "2026-07-11 세계뉴스 브리핑" in day  # h1 + og:title
    assert "<h1" in day

    index = (out_dir / "index.html").read_text(encoding="utf-8")
    assert 'rel="canonical" href="https://valueinfomaker-lab.github.io/worldnews-archive/"' in index


def test_build_emits_structured_data_and_meta(tmp_path):
    import json as _json

    data_dir = tmp_path / "data"
    out_dir = tmp_path / "docs"
    data_dir.mkdir()
    _write_day(data_dir, "2026-07-11", [_art("020/1", "가")], [_cls("020/1", "아세안")])
    build(data_dir=data_dir, output_dir=out_dir)

    day = (out_dir / "2026-07-11.html").read_text(encoding="utf-8")
    assert 'apple-touch-icon' in day and "assets/icon.png" in day
    assert 'property="og:locale" content="ko_KR"' in day
    # JSON-LD 는 유효 JSON이어야 하고 Organization/WebSite 를 담아야 한다
    block = day.split('application/ld+json">', 1)[1].split("</script>", 1)[0]
    graph = _json.loads(block)["@graph"]
    types = {n["@type"] for n in graph}
    assert {"Organization", "WebSite"} <= types
    # 날짜 페이지 description 은 그 날짜/건수를 담는다
    assert '2026-07-11 세계뉴스 일일 브리핑' in day
    assert (out_dir / "assets" / "icon.png").exists()

    index = (out_dir / "index.html").read_text(encoding="utf-8")
    assert "<title>GRIP — 세계뉴스 일일 브리핑</title>" in index


def test_build_index_groups_dates_by_month(tmp_path):
    data_dir = tmp_path / "data"
    out_dir = tmp_path / "docs"
    data_dir.mkdir()
    # 두 달에 걸친 3일
    _write_day(data_dir, "2026-07-12", [_art("020/1", "가")], [_cls("020/1", "아세안")])
    _write_day(data_dir, "2026-07-11", [_art("020/2", "나")], [_cls("020/2", "중국")])
    _write_day(data_dir, "2026-06-30", [_art("020/3", "다")], [_cls("020/3", "선진국")])
    build(data_dir=data_dir, output_dir=out_dir)

    index = (out_dir / "index.html").read_text(encoding="utf-8")
    assert "2026년 7월" in index and "2026년 6월" in index
    assert index.count("<details class=\"month\"") == 2
    # 최신 달(7월)만 펼쳐짐
    assert '<details class="month" open>' in index
    assert "전체 3일치" in index


def test_build_empty_day_renders_placeholder(tmp_path):
    data_dir = tmp_path / "data"
    out_dir = tmp_path / "docs"
    data_dir.mkdir()
    # 모든 기사가 해당없음 → 표시 권역 0
    _write_day(data_dir, "2026-07-11", [_art("020/1", "가")], [_cls("020/1", "해당없음")])
    build(data_dir=data_dir, output_dir=out_dir)
    page = (out_dir / "2026-07-11.html").read_text(encoding="utf-8")
    assert "해당 권역 기사가 없습니다" in page
