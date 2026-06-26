// ============================================================================
//  theme.js — light/dark theme toggle (for comparing the two looks)
//  Light = the current clean app theme. Dark = the original dashboard's teal style.
//  Adds a floating button on every page; remembers your choice.
// ============================================================================
(function () {
  const KEY = "ma-theme";
  const saved = localStorage.getItem(KEY) || "light";
  document.documentElement.setAttribute("data-theme", saved);

  const css = `
  :root[data-theme="dark"]{
    --ink:#EAF1F5; --soft:#90a6b4; --line:#26384a; --paper:#16242f; --card:#16242f; --hush:#0f1c26;
    --blue:#1b89aa; --blue2:#27a0c4;
    --green:#7fd6c2; --greenbg:#143029; --amber:#e3b264; --amberbg:#2c2613;
    --red:#e8857f; --redbg:#33201f; --pur:#b9a3e6; --faint:#90a6b4;
  }
  [data-theme="dark"] body{background:var(--hush);color:var(--ink)}
  [data-theme="dark"] header, [data-theme="dark"] .nav{background:rgba(15,28,38,.85)!important;border-color:var(--line)}
  [data-theme="dark"] input, [data-theme="dark"] select, [data-theme="dark"] textarea{background:#0f1c26!important;color:var(--ink);border-color:var(--line)}
  [data-theme="dark"] .ac-list{background:var(--paper)!important;border-color:var(--line)}
  [data-theme="dark"] tbody tr.sel, [data-theme="dark"] tbody tr.atm{background:#1c3340!important}
  [data-theme="dark"] .v-safe{background:#15323e!important;color:var(--green)}
  [data-theme="dark"] .r-maybe{background:var(--amberbg)!important;color:var(--amber)}
  [data-theme="dark"] .plan.paid{background:var(--amberbg)!important;color:var(--amber)}
  [data-theme="dark"] .note{background:#22240f!important;border-color:#4a3f1e!important;color:var(--amber)}
  [data-theme="dark"] .corrwarn{background:#22240f!important;border-color:#4a3f1e!important;color:var(--amber)!important}
  [data-theme="dark"] .warn{color:var(--red)!important;border-color:#5a2a25!important}
  [data-theme="dark"] .logout, [data-theme="dark"] .sell{background:var(--paper)!important;color:var(--ink)}
  [data-theme="dark"] .sell{color:var(--blue)}
  [data-theme="dark"] .v-lev{background:#241a33!important;color:var(--pur)}
  [data-theme="dark"] .empty{background:var(--paper);border-color:var(--line)}
  #themeBtn{position:fixed;left:18px;bottom:18px;z-index:60;height:40px;padding:0 16px;border-radius:980px;
    border:1px solid var(--line);background:var(--paper);color:var(--ink);
    font:600 13px/1 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;cursor:pointer;
    box-shadow:0 6px 18px rgba(0,0,0,.18);display:flex;align-items:center;gap:8px}
  #themeBtn:hover{filter:brightness(1.06)}
  @media(max-width:640px){#themeBtn{bottom:14px;top:auto;left:12px;height:34px;padding:0 12px;font-size:12px}}
  `;
  const st = document.createElement("style");
  st.textContent = css;
  document.head.appendChild(st);

  const label = (t) => (t === "dark" ? "☀️ Light theme" : "🌙 Dark theme");
  function addBtn() {
    if (document.getElementById("themeBtn")) return;
    const btn = document.createElement("button");
    btn.id = "themeBtn";
    btn.textContent = label(document.documentElement.getAttribute("data-theme"));
    btn.onclick = () => {
      const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem(KEY, next);
      btn.textContent = label(next);
    };
    document.body.appendChild(btn);
  }
  if (document.body) addBtn();
  else document.addEventListener("DOMContentLoaded", addBtn);
})();
