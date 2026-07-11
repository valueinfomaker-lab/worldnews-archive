"use strict";

/* ---- 테마 토글 ---------------------------------------------------------- */
(function theme() {
  const btn = document.getElementById("theme-toggle");
  const icon = () => {
    const dark = document.documentElement.getAttribute("data-theme") === "dark";
    if (btn) btn.textContent = dark ? "☀" : "🌙";
  };
  icon();
  if (btn) {
    btn.addEventListener("click", () => {
      const dark = document.documentElement.getAttribute("data-theme") === "dark";
      const next = dark ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
      icon();
    });
  }
})();

/* ---- 주제 필터 + 검색 --------------------------------------------------- */
(function filterSearch() {
  const search = document.getElementById("search");
  const filters = document.getElementById("topic-filters");
  const items = Array.from(document.querySelectorAll(".item"));
  if (!items.length) return;

  const countEl = document.getElementById("visible-count");
  const noResults = document.getElementById("no-results");
  let activeTopic = "";
  let query = "";

  function apply() {
    let visible = 0;
    for (const item of items) {
      const topics = (item.getAttribute("data-topics") || "").split(",");
      const text = item.getAttribute("data-search") || "";
      const okTopic = !activeTopic || topics.includes(activeTopic);
      const okQuery = !query || text.indexOf(query) !== -1;
      const show = okTopic && okQuery;
      item.hidden = !show;
      if (show) visible++;
    }
    // 빈 권역 숨기고 권역별 노출 수 갱신
    for (const section of document.querySelectorAll("[data-region]")) {
      const shown = section.querySelectorAll(".item:not([hidden])").length;
      section.hidden = shown === 0;
      const rc = section.querySelector(".rcount");
      if (rc) rc.textContent = shown;
    }
    if (countEl) countEl.textContent = visible;
    if (noResults) noResults.hidden = visible !== 0;
  }

  if (search) {
    search.addEventListener("input", () => {
      query = search.value.trim().toLowerCase();
      apply();
    });
  }
  if (filters) {
    filters.addEventListener("click", (e) => {
      const chip = e.target.closest("[data-topic]");
      if (!chip) return;
      activeTopic = chip.getAttribute("data-topic");
      for (const c of filters.querySelectorAll(".chip")) c.classList.toggle("is-active", c === chip);
      apply();
    });
  }
})();

/* ---- 맨 위로 ------------------------------------------------------------ */
(function toTop() {
  const btn = document.getElementById("to-top");
  if (!btn) return;
  const onScroll = () => { btn.hidden = window.scrollY < 400; };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
  btn.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
})();
