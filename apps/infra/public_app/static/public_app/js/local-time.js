/* Rewrites <time data-local-time datetime="ISO"> into the viewer's locale and time zone. */
(function () {
  function format(iso) {
    var date = new Date(iso);
    if (isNaN(date.getTime())) return null;
    var lang = document.documentElement.lang || undefined;
    try {
      return new Intl.DateTimeFormat(lang, {
        dateStyle: "long",
        timeStyle: "short",
      }).format(date);
    } catch (err) {
      return date.toLocaleString();
    }
  }

  function localize(el) {
    var text = format(el.getAttribute("datetime"));
    if (text) el.textContent = text;
  }

  function localizeAll() {
    document.querySelectorAll("time[data-local-time]").forEach(localize);
  }

  window.scitexLocalizeTime = localize;
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", localizeAll);
  } else {
    localizeAll();
  }
})();
