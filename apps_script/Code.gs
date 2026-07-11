/**
 * GRIP 뉴스레터 구독 폼 수신 → 구글 시트에 행 추가.
 *
 * 배포 방법(한 번만):
 *   1) 구독자를 담을 새 구글 시트를 만든다.
 *   2) 확장 프로그램 > Apps Script 를 열고 이 파일 내용을 붙여넣는다.
 *   3) 배포 > 새 배포 > 유형: 웹 앱
 *        - 실행 계정: 나
 *        - 액세스 권한: 모든 사용자
 *   4) 발급된 웹 앱 URL(.../exec)을 사이트 config 의 SUBSCRIBE_ENDPOINT 에 넣는다.
 *
 * 폼은 text/plain 본문(JSON 문자열)으로 POST 하므로 CORS 프리플라이트가 없다.
 */

const SHEET_NAME = "Subscribers";

function doPost(e) {
  try {
    const raw = (e && e.postData && e.postData.contents) || "{}";
    const body = JSON.parse(raw);
    const name = String(body.name || "").trim();
    const email = String(body.email || "").trim().toLowerCase();
    const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

    if (!name || !emailOk) {
      return json({ ok: false, error: "invalid" });
    }

    const sheet = getSheet();
    const lastRow = sheet.getLastRow();
    if (lastRow >= 2) {
      const emails = sheet.getRange(2, 3, lastRow - 1, 1).getValues();
      const dup = emails.some((row) => String(row[0]).trim().toLowerCase() === email);
      if (dup) {
        return json({ ok: true, duplicate: true });
      }
    }

    sheet.appendRow([new Date(), name, email]);
    return json({ ok: true });
  } catch (err) {
    return json({ ok: false, error: "server" });
  }
}

function doGet() {
  return json({ ok: true, service: "grip-subscribe" });
}

function getSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow(["신청일시", "이름", "이메일"]);
  }
  return sheet;
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(
    ContentService.MimeType.JSON
  );
}
