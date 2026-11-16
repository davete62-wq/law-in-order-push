// js/theme.js — Light / dark mode toggle, persisted in localStorage

(function () {
  const root = document.documentElement;
  const btn  = document.getElementById("theme-toggle");

  // Apply saved theme on load
  const saved = localStorage.getItem("theme") || "light";
  root.setAttribute("data-theme", saved);
  updateIcon(saved);

  if (btn) {
    btn.addEventListener("click", () => {
      const current = root.getAttribute("data-theme");
      const next    = current === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      localStorage.setItem("theme", next);
      updateIcon(next);
    });
  }

  function updateIcon(theme) {
    if (btn) btn.textContent = theme === "dark" ? "☀️" : "🌙";
  }
})();
