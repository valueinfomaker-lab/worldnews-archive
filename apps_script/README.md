# 뉴스레터 구독 백엔드 (Google Apps Script)

정적 사이트(GitHub Pages/Vercel)에는 서버가 없으므로, 구독 폼 데이터는
구글 시트에 붙이는 **Apps Script 웹앱**이 받는다.

## 데이터 흐름

```
사이트 구독 폼(index) ──POST(JSON, text/plain)──▶ Apps Script 웹앱 ──appendRow──▶ 구글 시트(Subscribers)
```

- `assets/subscribe.js` 가 이름·이메일을 검증한 뒤 `config.SUBSCRIBE_ENDPOINT` 로 POST.
- `Code.gs` 의 `doPost` 가 이메일 재검증 + 중복 확인 후 `[신청일시, 이름, 이메일]` 행 추가.
- 응답: `{ok:true}` / `{ok:true, duplicate:true}` / `{ok:false, error:...}`.

## 설치(한 번만)

1. **시트 생성**: 새 구글 시트를 만든다(제목 예: `GRIP 구독자`). 소유자는 본인.
2. **스크립트 붙여넣기**: 시트에서 `확장 프로그램 > Apps Script` → `Code.gs` 내용 전체 붙여넣기 → 저장.
3. **웹앱 배포**: `배포 > 새 배포` → 유형 **웹 앱**
   - 실행 계정: **나**
   - 액세스 권한: **모든 사용자**
   - 배포 → 권한 승인(최초 1회) → **웹 앱 URL**(`.../exec`) 복사.
4. **엔드포인트 연결**: 아래 중 하나로 URL을 사이트에 넣는다.
   - 배포 스크립트에 환경변수로: `export GRIP_SUBSCRIBE_ENDPOINT="https://script.google.com/.../exec"`
   - 또는 `generator/config.py` 의 `SUBSCRIBE_ENDPOINT` 기본값에 직접 기입.
5. **재빌드·배포**: `scripts/build_and_publish.sh` 실행.

> URL은 비밀이 아니다(공개 폼 제출용). 시트 편집 권한은 URL로 노출되지 않는다.

## 향후 뉴스레터 발송

기존 브리핑 파이프라인(`korean_worldnews_dailybriefing`)의 mailer가 이 시트의
`이메일` 열을 수신자 목록으로 읽어 발송하도록 확장할 수 있다. (별도 작업)

## CORS 참고

폼은 커스텀 헤더 없이 문자열 본문으로 POST 하므로 `Content-Type: text/plain` 이 되어
프리플라이트가 발생하지 않는다. 만약 특정 환경에서 응답 읽기가 막히면 `subscribe.js` 의
fetch 를 `mode:"no-cors"` + 낙관적 성공 표시로 바꾸면 된다(중복/에러 피드백은 포기).
