/**
 * GRIP 뉴스레터 구독 백엔드 (Google Apps Script 웹앱).
 *
 * 기능:
 *   - doPost {name,email}            : 구독 신청(중복/재구독 처리) → 시트에 행 추가
 *   - doGet ?action=list&key=...     : 활성 구독자 목록(JSON). 발송 파이프라인이 호출.
 *   - doGet ?action=unsubscribe&email=&token= : 수신거부(HTML 확인 페이지)
 *   - doGet (기본)                   : 헬스체크 JSON
 *
 * 비밀값은 코드가 아니라 스크립트 속성에 둔다(이 파일은 공개 저장소에 커밋됨):
 *   프로젝트 설정 > 스크립트 속성 에 LIST_KEY, UNSUB_SECRET 를 추가.
 *
 * 시트 컬럼: A 신청일시 | B 이름 | C 이메일 | D 상태('구독'/'구독취소')
 */

const SHEET_NAME = "Subscribers";
const STATUS_ACTIVE = "구독";
const STATUS_UNSUB = "구독취소";
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(10000);
  } catch (err) {
    return json({ ok: false, error: "busy" });
  }
  try {
    const body = JSON.parse((e && e.postData && e.postData.contents) || "{}");
    const name = String(body.name || "").trim();
    const email = normEmail(body.email);
    if (!name || !EMAIL_RE.test(email)) {
      return json({ ok: false, error: "invalid" });
    }

    const sheet = getSheet();
    const row = findRow(sheet, email);
    if (row) {
      const status = String(sheet.getRange(row, 4).getValue()).trim();
      if (status === STATUS_UNSUB) {
        sheet.getRange(row, 1).setValue(new Date());
        sheet.getRange(row, 4).setValue(STATUS_ACTIVE);
        return json({ ok: true, reactivated: true });
      }
      return json({ ok: true, duplicate: true });
    }
    sheet.appendRow([new Date(), name, email, STATUS_ACTIVE]);
    return json({ ok: true });
  } catch (err) {
    return json({ ok: false, error: "server" });
  } finally {
    lock.releaseLock();
  }
}

function doGet(e) {
  const params = (e && e.parameter) || {};
  if (params.action === "list") return listAction(params);
  if (params.action === "unsubscribe") return unsubscribeAction(params);
  return json({ ok: true, service: "grip-subscribe" });
}

function listAction(params) {
  const key = getProp("LIST_KEY");
  if (!key || params.key !== key) {
    return json({ ok: false, error: "unauthorized" });
  }
  const sheet = getSheet();
  const lastRow = sheet.getLastRow();
  const subs = [];
  if (lastRow >= 2) {
    const rows = sheet.getRange(2, 2, lastRow - 1, 3).getValues(); // B,C,D
    for (let i = 0; i < rows.length; i++) {
      const email = String(rows[i][1]).trim();
      const status = String(rows[i][2]).trim();
      if (email && status !== STATUS_UNSUB) {
        subs.push({ name: String(rows[i][0]).trim(), email: email });
      }
    }
  }
  return json({ ok: true, subscribers: subs });
}

function unsubscribeAction(params) {
  const secret = getProp("UNSUB_SECRET");
  const email = normEmail(params.email);
  const token = String(params.token || "");
  if (!secret || !email || hmacHex(email, secret) !== token) {
    return htmlPage("수신거부 링크가 올바르지 않습니다.", false);
  }
  const sheet = getSheet();
  const row = findRow(sheet, email);
  if (row) {
    sheet.getRange(row, 4).setValue(STATUS_UNSUB);
  }
  return htmlPage("수신거부가 완료되었습니다.<br>더 이상 뉴스레터를 받지 않습니다.", true);
}

/* ---- 유틸 ---------------------------------------------------------------- */

function normEmail(value) {
  return String(value || "").trim().toLowerCase();
}

function getProp(name) {
  return PropertiesService.getScriptProperties().getProperty(name);
}

function getSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow(["신청일시", "이름", "이메일", "상태"]);
  } else if (String(sheet.getRange(1, 4).getValue()).trim() !== "상태") {
    sheet.getRange(1, 4).setValue("상태");
  }
  return sheet;
}

function findRow(sheet, email) {
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return 0;
  const emails = sheet.getRange(2, 3, lastRow - 1, 1).getValues();
  for (let i = 0; i < emails.length; i++) {
    if (normEmail(emails[i][0]) === email) return i + 2;
  }
  return 0;
}

// Python hmac.new(secret, email, sha256).hexdigest() 와 동일한 소문자 hex.
function hmacHex(message, secret) {
  const bytes = Utilities.computeHmacSha256Signature(message, secret);
  let hex = "";
  for (let i = 0; i < bytes.length; i++) {
    const v = (bytes[i] < 0 ? bytes[i] + 256 : bytes[i]).toString(16);
    hex += v.length === 1 ? "0" + v : v;
  }
  return hex;
}

function json(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(
    ContentService.MimeType.JSON
  );
}

function htmlPage(message, ok) {
  const color = ok ? "#1a5490" : "#c0392b";
  const html =
    '<!doctype html><html lang="ko"><head><meta charset="utf-8">' +
    '<meta name="viewport" content="width=device-width, initial-scale=1">' +
    "<title>GRIP 뉴스레터</title></head>" +
    '<body style="font-family:-apple-system,sans-serif;max-width:480px;margin:80px auto;' +
    'padding:0 20px;text-align:center;color:#1a1a1a">' +
    '<div style="font-weight:800;font-size:22px;letter-spacing:-.02em;margin-bottom:18px">' +
    'GR<span style="color:#d99f45">I</span>P</div>' +
    '<p style="font-size:15px;line-height:1.6;color:' + color + '">' + message + "</p>" +
    "</body></html>";
  return HtmlService.createHtmlOutput(html);
}
