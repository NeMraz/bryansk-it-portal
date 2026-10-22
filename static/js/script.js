(function () {
  /* ---------- Переключатель темы оформления ---------- */

  var html = document.documentElement;
  var themeButton = document.querySelector(".theme-toggle");
  var storedTheme = localStorage.getItem("theme");
  var prefersDark = window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;

  // Определяем стартовую тему: из localStorage, затем из системных настроек,
  // иначе — светлая.
  function resolveTheme() {
    if (storedTheme === "dark" || (!storedTheme && prefersDark)) {
      return "dark";
    }
    return "light";
  }

  function applyTheme(theme) {
    html.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);

    var icon = themeButton && themeButton.querySelector(".theme-icon");
    if (icon) {
      icon.textContent = theme === "dark" ? "☀️" : "🌙";
    }
    if (themeButton) {
      themeButton.setAttribute(
        "aria-label",
        theme === "dark" ? "Переключить на светлую тему" : "Переключить на темную тему"
      );
      themeButton.setAttribute(
        "title",
        theme === "dark" ? "Темная тема включена" : "Темная тема выключена"
      );
    }
  }

  if (themeButton) {
    // Создаём иконку внутри кнопки, если её нет.
    if (!themeButton.querySelector(".theme-icon")) {
      var icon = document.createElement("span");
      icon.className = "theme-icon";
      icon.textContent = "🌙";
      themeButton.appendChild(icon);
      themeButton.setAttribute("title", "Темная тема выключена");
      themeButton.setAttribute("aria-label", "Переключить на темную тему");
    }

    applyTheme(resolveTheme());

    themeButton.addEventListener("click", function () {
      var current = html.getAttribute("data-theme");
      var next = current === "dark" ? "light" : "dark";
      applyTheme(next);
    });
  }

  /* ---------- Мобильное меню ---------- */

  var button = document.querySelector(".nav-toggle");
  var nav = document.getElementById("site-nav");
  var links = nav && nav.querySelectorAll("a");
  if (!button || !nav) return;

  button.addEventListener("click", function () {
    var isOpen = nav.classList.toggle("open");
    button.setAttribute("aria-expanded", isOpen ? "true" : "false");
  });

  if (links) {
    links.forEach(function (link) {
      link.addEventListener("click", function () {
        if (nav.classList.contains("open")) {
          nav.classList.remove("open");
          button.setAttribute("aria-expanded", "false");
        }
      });
    });
  }
})();
