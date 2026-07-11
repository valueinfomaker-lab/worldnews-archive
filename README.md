# 세계뉴스 일일 브리핑 — 날짜별 공개 아카이브

형제 앱 [`korean_worldnews_dailybriefing`](../korean_worldnews_dailybriefing)이 매일 08:00에
생성하는 브리핑 데이터(`data/briefing_YYYY-MM-DD.json`)를 읽어, **날짜별 정적 사이트**를
만들어 GitHub Pages로 공개한다. 각 페이지에는 카톡/이메일로 바로 붙여넣는 **복사 버튼**이 있다.

- 정적 사이트 → 서버·DB 불필요. 데이터가 하루 1회만 바뀌므로 배치 재생성이 적합.
- 복사 버튼은 브라우저 클립보드 API로 동작(클라이언트 전용).
- 형제 앱은 수정하지 않는다. 데이터만 읽는다.

## 구조

```
generator/   # 빌드 로직 (core=vendored 선별, load=JSON 로더, payloads=복사본문, build=오케스트레이터)
templates/   # Jinja2 (base / index / day)
assets/      # style.css, copy.js  → docs/assets 로 복사
docs/        # 빌드 출력 = GitHub Pages 배포 대상
scripts/build_and_publish.sh   # 빌드 → 변경시 커밋·푸시
com.joseph.worldnews-archive.plist  # 별도 LaunchAgent(매일 08:20)
```

## 빌드 & 로컬 확인

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m generator.build            # docs/ 생성
.venv/bin/python -m http.server 8000 --directory docs
# http://localhost:8000/ 접속
```

**복사 버튼은 secure context(HTTPS 또는 localhost)에서만 동작한다.** `file://`로 직접 열면
클립보드 API가 막혀 폴백(execCommand)만 동작한다. 반드시 `http://localhost` 또는 배포된
HTTPS URL에서 확인할 것.

## 배포 (GitHub Pages)

공개 repo `valueinfomaker-lab/worldnews-archive`, Pages 소스 = `main` 브랜치 `/docs`.
URL: `https://valueinfomaker-lab.github.io/worldnews-archive/`

```bash
scripts/build_and_publish.sh    # 수동 1회 배포
```

## 자동화

`com.joseph.worldnews-archive.plist`를 `~/Library/LaunchAgents/`에 설치하면 매일 08:20
(형제 앱 08:00 이후) 자동으로 빌드·배포한다. **LaunchAgent**(GUI 세션)여야 osxkeychain의
gh 토큰으로 push가 된다.

```bash
cp com.joseph.worldnews-archive.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.joseph.worldnews-archive.plist
```

## 테스트

```bash
.venv/bin/python -m pytest        # core/load/payloads/build/sync
```

`tests/test_sync.py`는 형제 repo가 같은 머신에 있으면 vendored 사본(REGIONS/select/렌더 형식)이
원본과 동일한지 검증한다. 형제 앱이 권역을 바꾸면 여기서 실패하므로 `generator/core.py`를
맞춰 갱신하면 된다.
