"use strict";

/* 뉴스레터 구독 폼 → Google Apps Script 웹앱으로 POST.
   text/plain 본문(기본값)이라 CORS 프리플라이트가 없다(simple request). */
(function subscribe() {
  const form = document.getElementById("subscribe-form");
  if (!form) return;

  const status = document.getElementById("sub-status");
  const nameEl = document.getElementById("sub-name");
  const emailEl = document.getElementById("sub-email");
  const btn = form.querySelector(".sub-btn");
  const endpoint = (form.getAttribute("data-endpoint") || "").trim();
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function show(message, kind) {
    if (!status) return;
    status.textContent = message;
    status.className = "sub-status is-" + kind;
    status.hidden = false;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = nameEl.value.trim();
    const email = emailEl.value.trim();

    if (!name) {
      show("이름을 입력해 주세요.", "error");
      nameEl.focus();
      return;
    }
    if (!EMAIL_RE.test(email)) {
      show("올바른 이메일 주소를 입력해 주세요.", "error");
      emailEl.focus();
      return;
    }
    if (!endpoint) {
      show("구독 기능을 준비 중입니다. 잠시 후 다시 시도해 주세요.", "error");
      return;
    }

    btn.disabled = true;
    show("신청 중…", "pending");
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        body: JSON.stringify({ name, email }),
      });
      const data = await res.json().catch(() => ({ ok: res.ok }));
      if (data && data.ok) {
        form.reset();
        show(
          data.duplicate
            ? "이미 구독 중인 이메일입니다."
            : "구독 신청이 완료되었습니다. 감사합니다!",
          "ok"
        );
      } else {
        show("신청에 실패했습니다. 잠시 후 다시 시도해 주세요.", "error");
      }
    } catch (err) {
      show("네트워크 오류로 신청하지 못했습니다. 잠시 후 다시 시도해 주세요.", "error");
    } finally {
      btn.disabled = false;
    }
  });
})();
