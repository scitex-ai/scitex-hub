// Security Scan Button Handler
// Triggers a security scan via AJAX and displays results

(function () {
  "use strict";

  interface SecurityScanResponse {
    success: boolean;
    alerts?: {
      critical: number;
      high: number;
      medium: number;
      low: number;
    };
    error?: string;
  }

  document.addEventListener("DOMContentLoaded", function () {
    const runScanBtn = document.getElementById(
      "runScanBtn",
    ) as HTMLButtonElement | null;

    if (runScanBtn) {
      // Get CSRF token and API URL from data attributes
      const csrfTokenElement = document.querySelector(
        "[name=csrfmiddlewaretoken]",
      ) as HTMLInputElement | null;
      if (!csrfTokenElement) {
        console.error("CSRF token element not found");
        return;
      }

      const csrfToken = csrfTokenElement.value;
      const apiUrl = runScanBtn.dataset.scanUrl;

      if (!apiUrl) {
        console.error("Scan URL not found in button data attributes");
        return;
      }

      runScanBtn.addEventListener("click", function () {
        const btn = this as HTMLButtonElement;
        btn.disabled = true;
        btn.innerHTML =
          '<span class="spinner-border spinner-border-sm me-2"></span>Scanning...';

        fetch(apiUrl, {
          method: "POST",
          headers: {
            "X-CSRFToken": csrfToken,
            "Content-Type": "application/json",
          },
        })
          .then((response) => response.json() as Promise<SecurityScanResponse>)
          .then((data) => {
            if (data.success && data.alerts) {
              alert(
                `Scan completed!\nCritical: ${data.alerts.critical}\nHigh: ${data.alerts.high}\nMedium: ${data.alerts.medium}\nLow: ${data.alerts.low}`,
              );
              location.reload();
            } else {
              alert("Scan failed: " + (data.error || "Unknown error"));
              btn.disabled = false;
              btn.innerHTML = "Run security scan";
            }
          })
          .catch((error: Error) => {
            console.error("Error running scan:", error);
            alert("Error running scan: " + error.message);
            btn.disabled = false;
            btn.innerHTML = "Run security scan";
          });
      });
    }
  });
})();
