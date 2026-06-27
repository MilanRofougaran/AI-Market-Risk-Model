/* ============================================================================
 *  mobile-gate.js — RiskLens is a dense, data-rich desktop tool. On phones we
 *  show a clean "best on a computer" screen instead of the cramped layout.
 *  Targets PHONES only (iPhone/Android phones + very narrow screens).
 *  iPads, laptops and desktops are left untouched.
 * ========================================================================== */
(function () {
  var ua = navigator.userAgent || "";
  var isPhone =
    /iPhone|iPod|Android.*Mobile|webOS|BlackBerry|IEMobile|Opera Mini|Windows Phone/i.test(ua) ||
    (typeof window.innerWidth === "number" && window.innerWidth > 0 && window.innerWidth < 600);
  if (!isPhone) return;

  function gate() {
    if (document.getElementById("mobileGate")) return;
    var d = document.createElement("div");
    d.id = "mobileGate";
    d.setAttribute("role", "dialog");
    d.style.cssText =
      "position:fixed;inset:0;z-index:2147483647;background:#0a0a0a;color:#fff;" +
      "display:flex;flex-direction:column;align-items:center;justify-content:center;" +
      "text-align:center;padding:32px;box-sizing:border-box;" +
      "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;";
    d.innerHTML =
      '<svg width="56" height="56" viewBox="0 0 32 32" style="margin-bottom:20px" aria-hidden="true">' +
        '<rect width="32" height="32" rx="7" fill="#141416"></rect>' +
        '<path d="M5 11 L12 23 L18 16 L26 6" fill="none" stroke="#0071e3" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>' +
        '<circle cx="26" cy="6" r="2.7" fill="#0071e3"></circle>' +
      '</svg>' +
      '<div style="font-size:30px;font-weight:700;letter-spacing:-.02em;margin-bottom:14px">Risk<span style="color:#0071e3">Lens</span></div>' +
      '<div style="font-size:19px;font-weight:600;margin-bottom:10px">Best viewed on a computer</div>' +
      '<div style="font-size:15px;color:#a1a1a6;line-height:1.55;max-width:340px">' +
        'RiskLens is a detailed research tool built for a larger screen. Please open ' +
        '<b style="color:#fff">risklensapp.com</b> on a <b style="color:#fff">laptop or desktop</b> for the full experience.' +
      '</div>';
    (document.body || document.documentElement).appendChild(d);
    document.documentElement.style.overflow = "hidden";
    if (document.body) document.body.style.overflow = "hidden";
  }

  if (document.body) gate();
  else document.addEventListener("DOMContentLoaded", gate);
})();
