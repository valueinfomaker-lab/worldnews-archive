import json

from generator.load import load_days


def _write_day(data_dir, day, *, articles, classifications):
    (data_dir / f"briefing_{day}.json").write_text(
        json.dumps({"day": day, "articles": articles, "classifications": classifications}, ensure_ascii=False),
        encoding="utf-8",
    )


def _art(aid):
    return {"id": aid, "title": "제목", "press": "언론사", "lede": "요약",
            "url": f"https://n.news.naver.com/mnews/article/{aid}", "date": "20260711", "section": "231"}


def _cls(aid, region="아세안"):
    return {"id": aid, "region": region, "topics": ["경제"], "score": 70, "summary": "한 줄"}


def test_load_days_newest_first(tmp_path):
    _write_day(tmp_path, "2026-07-09", articles=[_art("020/1")], classifications=[_cls("020/1")])
    _write_day(tmp_path, "2026-07-11", articles=[_art("020/2")], classifications=[_cls("020/2")])
    _write_day(tmp_path, "2026-07-10", articles=[_art("020/3")], classifications=[_cls("020/3")])
    days = load_days(tmp_path)
    assert [d.day for d in days] == ["2026-07-11", "2026-07-10", "2026-07-09"]


def test_load_days_reconstructs_dataclasses(tmp_path):
    _write_day(tmp_path, "2026-07-11", articles=[_art("020/1")], classifications=[_cls("020/1", "중국")])
    (day,) = load_days(tmp_path)
    assert day.articles[0].title == "제목"
    assert day.classifications[0].region == "중국"
    assert day.classifications[0].topics == ("경제",)  # tuple 로 복원


def test_load_days_skips_corrupt_file(tmp_path):
    _write_day(tmp_path, "2026-07-11", articles=[_art("020/1")], classifications=[_cls("020/1")])
    (tmp_path / "briefing_2026-07-10.json").write_text("{ this is not json", encoding="utf-8")
    days = load_days(tmp_path)
    assert [d.day for d in days] == ["2026-07-11"]  # 손상 파일은 조용히 skip
