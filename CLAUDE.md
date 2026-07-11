# CLAUDE.md — GRIP 세계뉴스 아카이브 (공개 사이트)

KIEP 세계뉴스 브리핑의 **공개 열람용 정적 사이트**. 짝이 되는 파이프라인 앱
(`~/korean_worldnews_dailybriefing`)이 매일 만든 `data/briefing_*.json`을 읽어 **날짜별 정적
페이지 + 인덱스**를 `docs/`에 생성하고, GitHub Pages와 Vercel로 배포한다. 브랜드는 **GRIP
(Global Regional Intelligence Platform)** — 태그라인 "세계의 변화를 읽고, 비즈니스 기회를 연결합니다."

- 서버·DB 없음(정적). 하루 1회만 갱신, 열람은 읽기 전용.
- 자동화: launchd `com.joseph.worldnews-archive` **매일 08:20** (파이프라인 08:00 직후).

## 파이프라인과의 관계
- **데이터 입력**: 형제 저장소의 `data/briefing_*.json`을 읽는다(`generator/config.py`의 `DATA_DIR`).
- **vendored core**: `generator/core.py`는 파이프라인의 `REGIONS`/`TOPICS`/`Article`/`Classification`/
  `select()`를 **복사**한 것. `tests/test_sync.py`가 형제 저장소와 바이트 동등성을 검증 → **파이프라인이
  권역/로직을 바꾸면 여기 core도 같이 갱신**해야 sync 테스트 통과.
- **구독자 명단의 실제 저장소는 여기**(Apps Script + 구글 시트). 파이프라인이 이 사이트의 Apps Script
  엔드포인트를 호출해 목록을 읽고 뉴스레터를 발송한다.

## 구조
```
generator/            빌드 코드
  config.py           경로·SITE_*·TOP_N·SUBSCRIBE_ENDPOINT·SITE_URL·KAKAO_OPENCHAT_URL
  core.py             VENDORED: REGIONS/TOPICS/models/select (출처 주석)
  load.py             briefing_*.json 로드(손상 파일 skip)
  payloads.py         복사용 평문/HTML 페이로드 생성
  build.py            오케스트레이터  `python -m generator.build`
templates/            base / index / day (Jinja2, autoescape)
assets/               style.css, copy.js, ui.js, subscribe.js, og-image.png  (→ docs/assets 로 복사)
apps_script/          Code.gs(구독 백엔드) + README (구글 시트에 붙이는 코드)
docs/                 빌드 출력 = 배포 대상. .nojekyll, index.html, YYYY-MM-DD.html, dates.json, assets/
scripts/build_and_publish.sh   빌드→변경시 커밋·push
tests/                core/load/payloads/build/sync
vercel.json           outputDirectory=docs (정적)
com.joseph.worldnews-archive.plist   launchd 08:20
```

## 빌드 / 배포
```bash
.venv/bin/python -m generator.build      # docs/ 전체 재빌드(idempotent)
.venv/bin/python -m pytest -q
scripts/build_and_publish.sh             # 빌드 → git add docs → 변경시 commit → push origin main
```
- **GitHub Pages**: `valueinfomaker-lab/worldnews-archive`, main `/docs`. → `https://valueinfomaker-lab.github.io/worldnews-archive/`
- **Vercel**: git 연동 자동 배포. → `https://worldnewsarchivesite.vercel.app/`
- push 한 번으로 두 곳 모두 자동 재배포.

## GRIP 브랜드
- 컬러 토큰(`assets/style.css`): 네이비 `--accent: #1a5490`(인텔리전스) + 골드 `--gold: #d99f45`(기회 노드).
- 워드마크 `GR<i>I</i>P`(가운데 I만 골드). 로고 마크 = "자오선 G"(지구본+G 모노그램, 골드 노드) — `base.html.j2`의
  `#logo` SVG 심볼 + favicon 데이터 URI.
- 라이트/다크 양쪽 지원(CSS 변수 + `prefers-color-scheme` + `data-theme` 토글).

## 화면 기능
- 인덱스: GRIP 히어로 + 날짜 아카이브 목록 + **하단 연결 카드 2개**(뉴스레터 구독 / 카카오톡 오픈채팅).
- 날짜 페이지: 권역별 카드, 주제 필터·키워드 검색(`ui.js`), 날짜 이동, **복사 버튼**(카톡 평문 / 메일 서식, `copy.js`).
- 공유(OG): 모든 페이지 `<head>`에 og:*/twitter 메타 + `assets/og-image.png`(1200×630 GRIP 카드).

## 구독 백엔드 (Apps Script + 구글 시트)
정적 사이트라 폼 데이터는 **구글 시트에 붙인 Apps Script 웹앱**(`apps_script/Code.gs`)이 처리.
```
구독 폼(subscribe.js) ─POST(JSON,text/plain)→ Apps Script ─→ 시트(Subscribers: 신청일시·이름·이메일·상태)
파이프라인 ─GET ?action=list&key=─→ 활성 구독자 JSON
구독자(메일 링크) ─GET ?action=unsubscribe&email=&token=─→ 상태='구독취소'
```
- 비밀값은 **스크립트 속성** `LIST_KEY`·`UNSUB_SECRET`에 둔다(공개 저장소라 코드에 안 넣음). 파이프라인
  `.env`의 `NEWSLETTER_LIST_KEY`/`NEWSLETTER_UNSUB_SECRET`와 **정확히 동일**해야 함.
- 수신거부 토큰 = `HMAC-SHA256(email, UNSUB_SECRET)`. Apps Script `hmacHex`와 파이프라인
  `subscribers.unsubscribe_token`이 같은 결과여야 함(검증 완료).
- 엔드포인트 URL은 `generator/config.py`의 `SUBSCRIBE_ENDPOINT`(공개 폼용, 비밀 아님)로 사이트에 주입.

## 주의사항 / 하드-원 지식
- **Apps Script 재배포**: 코드/속성 변경 후 반드시 `배포 → 배포 관리 → 기존 웹앱 편집 → "새 버전"`.
  "새 배포"를 누르면 `/exec` **URL이 바뀐다**. 스크립트 속성은 실행 시점에 읽혀 재배포 불필요.
- **Apps Script POST 리다이렉트**: `/exec` POST는 302로 googleusercontent로 넘어감. 브라우저 fetch는
  자동으로 GET 전환해 처리하지만 `curl -X POST -L`은 깨진다(테스트 시 `--data`만, `-X POST` 금지).
- **CORS**: 폼은 헤더 없는 문자열 본문(→ `text/plain`)이라 프리플라이트 없음. Apps Script 첫 요청은 콜드스타트로
  느릴 수 있어 `subscribe.js`에 25초 타임아웃.
- **GitHub Pages 캐시**: assets는 ~10분 캐시. JS/CSS 바꿔도 잠깐 옛 버전이 보일 수 있음(새로고침/캐시만료 후 반영).
- **`.nojekyll` 필수**(밑줄/점 파일 누락 방지). 템플릿 파일명 앞자리 밑줄 금지.
- **jsonify 키 정렬**: (파이프라인 web.py 쪽) `app.json.sort_keys=False`로 REGIONS 순서 보존 — 참고.
- **카카오 OG 캐시**: 카톡은 링크 미리보기를 캐시. 갱신은 `developers.kakao.com/tool/clear/og` 또는 `?v=` 쿼리.

## 커밋/배포 관례
- 정적 출력 `docs/`는 **커밋 대상**(배포 소스). 소스 변경 후 `scripts/build_and_publish.sh`로 재빌드·push.
- `docs/`를 손으로 고치지 말 것 — 항상 `templates/`·`assets/`·`generator/`를 고치고 재빌드.
