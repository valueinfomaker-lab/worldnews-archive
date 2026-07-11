"use strict";

// 숨은 payload div 의 textContent 를 읽는다. 엔티티는 브라우저가 자동 디코딩해
// 원문 그대로(개행 포함) 돌려준다.
function payloadText(id) {
  const el = document.getElementById(id);
  return el ? el.textContent : "";
}

let toastTimer = null;
function toast(message) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = message;
  el.hidden = false;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.classList.remove("show");
    el.hidden = true;
  }, 1500);
}

function legacyCopy(text) {
  const ta = document.createElement("textarea");
  ta.value = text;
  ta.style.position = "fixed";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.focus();
  ta.select();
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch (e) {
    ok = false;
  }
  ta.remove();
  toast(ok ? "복사됨" : "복사 실패");
}

async function copyPlain(text) {
  try {
    await navigator.clipboard.writeText(text);
    toast("카톡용 평문 복사됨");
  } catch (e) {
    legacyCopy(text);
  }
}

async function copyRich(html, text) {
  try {
    const item = new ClipboardItem({
      "text/html": new Blob([html], { type: "text/html" }),
      "text/plain": new Blob([text], { type: "text/plain" }),
    });
    await navigator.clipboard.write([item]);
    toast("메일용 서식 복사됨");
  } catch (e) {
    // 서식 복사 미지원 → 평문으로 강등
    await copyPlain(text);
  }
}

document.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-copy]");
  if (!btn) return;
  const kind = btn.getAttribute("data-copy");
  const pt = btn.getAttribute("data-pt");
  const ht = btn.getAttribute("data-ht");
  if (kind === "rich") {
    copyRich(payloadText(ht), payloadText(pt));
  } else {
    copyPlain(payloadText(pt));
  }
});
