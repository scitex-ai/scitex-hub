/* Public Status Page — auto-refresh every 60s */
(function () {
  var REFRESH_MS = 60000;
  var API_URL = document.body.dataset.statusApiUrl;

  function refresh() {
    if (!API_URL) return;
    fetch(API_URL)
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        var banner = document.getElementById("overall-banner");
        banner.className = "status-banner status-banner--" + data.overall;
        if (data.overall === "operational") {
          banner.textContent = "All Systems Operational";
        } else if (data.overall === "degraded") {
          banner.textContent = "Partial System Outage";
        } else {
          banner.textContent = "Major System Outage";
        }
        document.getElementById("checked-at").textContent = data.checked_at;
      })
      .catch(function (err) {
        console.error("Status refresh failed:", err);
      });
  }

  setInterval(refresh, REFRESH_MS);
})();
