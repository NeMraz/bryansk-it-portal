(function () {
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
