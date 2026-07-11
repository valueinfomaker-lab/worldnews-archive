# 뉴스레터 구독 백엔드 (Google Apps Script)

정적 사이트(GitHub Pages/Vercel)에는 서버가 없으므로, 구독 폼 데이터와 목록 조회·수신거부를
구글 시트에 붙인 **Apps Script 웹앱**이 처리한다.

## 데이터 흐름

```
사이트 구독 폼 ──POST(JSON)──▶ Apps Script ──▶ 구글 시트(Subscribers: 신청일시·이름·이메일·상태)
브리핑 파이프라인 ──GET ?action=list&key=─▶ Apps Script ──▶ 활성 구독자 JSON ──▶ 개별 메일 발송
구독자(메일의 링크) ─GET ?action=unsubscribe&email=&token=─▶ Apps Script ──▶ 상태='구독취소'
```

## 엔드포인트

| 요청 | 설명 |
|---|---|
| `POST {name,email}` | 신규 구독. 이미 있으면 `{ok,duplicate}`, 취소했던 이메일이면 재활성 `{ok,reactivated}` |
| `GET ?action=list&key=LIST_KEY` | 활성 구독자 `{ok, subscribers:[{name,email}]}` (키 불일치 시 unauthorized) |
| `GET ?action=unsubscribe&email=&token=` | 토큰(=HMAC-SHA256(email, UNSUB_SECRET)) 검증 후 상태='구독취소', HTML 확인 페이지 |
| `GET` (기본) | 헬스체크 |

## 설치 / 갱신

1. **스크립트 갱신**: 구독 시트에서 `확장 프로그램 > Apps Script` → `Code.gs` 내용 전체를 최신본으로 교체 → 저장.
2. **스크립트 속성 추가**: `프로젝트 설정(⚙️) > 스크립트 속성 > 속성 추가` 로 두 개 등록
   - `LIST_KEY` = (파이프라인 .env 의 `NEWSLETTER_LIST_KEY` 와 동일한 값)
   - `UNSUB_SECRET` = (파이프라인 .env 의 `NEWSLETTER_UNSUB_SECRET` 와 동일한 값)
3. **재배포(같은 URL 유지)**: `배포 > 배포 관리 > (기존 웹앱) 편집(연필) > 버전: 새 버전 > 배포`.
   - ⚠️ "새 배포"를 누르면 URL이 바뀐다. 반드시 **기존 배포를 편집해 새 버전**으로 올려야 `/exec` URL이 유지된다.

> 비밀값은 코드에 넣지 않는다. `Code.gs` 는 공개 저장소에 커밋되므로 값은 스크립트 속성에만 둔다.

## 시트 컬럼

`A 신청일시 | B 이름 | C 이메일 | D 상태`. 기존 3컬럼 시트는 실행 시 D열 헤더('상태')가 자동 보강되며,
상태가 비어 있으면 활성으로 간주한다. 수신거부는 행을 지우지 않고 상태만 '구독취소'로 바꾼다(감사 목적).

## 발송 파이프라인 연결

`korean_worldnews_dailybriefing/.env` 에 아래 3개를 넣으면 08:00 자동 실행이 본 브리핑 발송 직후
활성 구독자에게 개별 발송한다(각 메일 하단에 수신거부 링크 포함).

```
NEWSLETTER_ENDPOINT=https://script.google.com/macros/s/…/exec
NEWSLETTER_LIST_KEY=<LIST_KEY 와 동일>
NEWSLETTER_UNSUB_SECRET=<UNSUB_SECRET 와 동일>
```

셋 중 하나라도 비면 구독자 발송은 건너뛰고 본 브리핑만 나간다.
