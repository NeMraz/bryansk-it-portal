(function () {
  /* ---------- Тема оформления ---------- */

  var html = document.documentElement;
  var themeButton = document.querySelector(".theme-toggle");

  function applyTheme(theme) {
    html.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
    if (themeButton) {
      themeButton.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
    }
  }

  if (themeButton) {
    var stored = localStorage.getItem("theme");
    var prefersDark = window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyTheme(stored || (prefersDark ? "dark" : "light"));

    themeButton.addEventListener("click", function () {
      applyTheme(html.getAttribute("data-theme") === "dark" ? "light" : "dark");
    });
  }

  /* ---------- Мобильное меню ---------- */

  var button = document.querySelector(".nav-toggle");
  var nav = document.getElementById("site-nav");
  if (!button || !nav) return;

  button.addEventListener("click", function () {
    var isOpen = nav.classList.toggle("open");
    button.setAttribute("aria-expanded", isOpen ? "true" : "false");
  });

  nav.querySelectorAll("a").forEach(function (link) {
    link.addEventListener("click", function () {
      nav.classList.remove("open");
      button.setAttribute("aria-expanded", "false");
    });
  });
})();
