// ============================================================================
//  mode.js — global Beginner / Expert switch (remembered like the theme).
//  Beginner = plain-English cards anyone can read. Expert = the full data view.
//  Sets data-mode on <html>, persists the choice, and fires a "modechange" event
//  so each page can re-render. Pages add their own toggle button that calls
//  window.toggleMode() and their own beginner/expert rendering.
// ============================================================================
(function () {
  const KEY = "ma-mode";
  window.MA_MODE = localStorage.getItem(KEY) || "expert";   // default: expert (impress first-time / pro visitors; beginners can switch)
  document.documentElement.setAttribute("data-mode", window.MA_MODE);

  window.setMode = (m) => {
    window.MA_MODE = m;
    localStorage.setItem(KEY, m);
    document.documentElement.setAttribute("data-mode", m);
    document.dispatchEvent(new CustomEvent("modechange", { detail: m }));
    // keep any on-page toggle labels in sync
    document.querySelectorAll("[data-modeswitch]").forEach(syncSwitch);
  };
  window.toggleMode = () => window.setMode(window.MA_MODE === "beginner" ? "expert" : "beginner");

  function syncSwitch(el) {
    const isBeg = window.MA_MODE === "beginner";
    el.querySelectorAll("[data-mode-opt]").forEach(b => {
      b.classList.toggle("on", b.getAttribute("data-mode-opt") === window.MA_MODE);
    });
    el.setAttribute("aria-label", isBeg ? "Beginner view" : "Expert view");
  }
  // expose for pages that build the switch after load
  window.syncModeSwitch = () => document.querySelectorAll("[data-modeswitch]").forEach(syncSwitch);

  document.addEventListener("DOMContentLoaded", window.syncModeSwitch);
})();
