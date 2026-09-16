/* Public Status Page — auto-refresh every 60s */
(function () {
  var REFRESH_MS = 60000;
  var API_URL = document.body.dataset.statusApiUrl;
  var OVERALL_STATES = ["operational", "degraded", "partial_outage", "down"];

  // Labels are rendered translated by the template, so JS never holds English copy.
  function overallLabel(banner, overall) {
    var key = OVERALL_STATES.indexOf(overall) === -1 ? "down" : overall;
    return banner.getAttribute("data-label-" + key.replace("_", "-"));
  }

  function refresh() {
    if (!API_URL) return;
    fetch(API_URL)
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        var banner = document.getElementById("overall-banner");
        banner.className = "status-banner status-banner--" + data.overall;
        var label = overallLabel(banner, data.overall);
        if (label) banner.textContent = label;
        var checkedAt = document.getElementById("checked-at");
        checkedAt.setAttribute("datetime", data.checked_at);
        if (window.scitexLocalizeTime) window.scitexLocalizeTime(checkedAt);
      })
      .catch(function (err) {
        console.error("Status refresh failed:", err);
      });
  }

  setInterval(refresh, REFRESH_MS);
})();
