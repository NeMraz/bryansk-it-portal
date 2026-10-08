(function () {
  var button = document.querySelector(".nav-toggle");
  var nav = document.getElementById("site-nav");
  if (!button || !nav) return;

  button.addEventListener("click", function () {
    var isOpen = nav.classList.toggle("open");
    button.setAttribute("aria-expanded", isOpen ? "true" : "false");
  });
})();
