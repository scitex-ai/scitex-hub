/**
 * Dev Tools TypeScript
 * Functions for footer dev toolbar (DEBUG mode only)
 * Handles development-only maintenance actions.
 */

// Get CSRF token from cookie
function getCsrfToken(): string {
  const name = "csrftoken";
  let cookieValue = "";
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

/**
 * POST to a development endpoint with button feedback.
 */
async function devToolAction(
  btnId: string,
  url: string,
  originalIcon: string,
  formatSuccess: (data: any) => string,
): Promise<void> {
  const btn = document.getElementById(btnId) as HTMLButtonElement | null;

  if (btn) {
    btn.disabled = true;
    btn.style.opacity = "0.6";
    const icon = btn.querySelector("i");
    if (icon) {
      icon.className = "fas fa-spinner fa-spin";
    }
  }

  try {
    const csrfToken = getCsrfToken();
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
    });

    const data = await response.json();

    if (response.ok) {
      if (btn) {
        const icon = btn.querySelector("i");
        if (icon) {
          icon.className = "fas fa-check";
          icon.style.color = "#22c55e";
        }
      }
      alert(formatSuccess(data));
      window.location.reload();
    } else {
      if (btn) {
        const icon = btn.querySelector("i");
        if (icon) {
          icon.className = "fas fa-times";
          icon.style.color = "#ef4444";
        }
      }
      alert(`Failed: ${data.error || data.message || "Unknown error"}`);
    }
  } catch (error) {
    console.error(`Dev tool action failed (${url}):`, error);
    if (btn) {
      const icon = btn.querySelector("i");
      if (icon) {
        icon.className = "fas fa-times";
        icon.style.color = "#ef4444";
      }
    }
    alert("Action failed. Check console for details.");
  } finally {
    setTimeout(() => {
      if (btn) {
        btn.disabled = false;
        btn.style.opacity = "1";
        const icon = btn.querySelector("i");
        if (icon) {
          icon.className = `fas ${originalIcon}`;
          icon.style.color = "";
        }
      }
    }, 2000);
  }
}

// Cancel all SLURM jobs (Dev only)
async function cancelAllJobs(): Promise<void> {
  if (!confirm("Cancel ALL SLURM jobs?")) return;
  await devToolAction(
    "cancel-all-jobs-btn",
    "/dev/api/cancel-all-jobs/",
    "fa-ban",
    (data) => `Jobs Cancelled!\n\n${data.message}`,
  );
}

// Make the function available globally for the footer's onclick handler.
(window as any).cancelAllJobs = cancelAllJobs;
