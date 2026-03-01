/**
 * Dev Tools TypeScript
 * Functions for footer dev toolbar (DEBUG mode only)
 * Handles visitor pool management: init, fill slots, free slots
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
 * Helper: POST to a visitor pool API endpoint with button feedback
 */
async function visitorPoolAction(
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
      alert(`Failed: ${data.error || "Unknown error"}`);
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

// Initialize Visitor Pool (Dev only)
async function initVisitorPool(): Promise<void> {
  await visitorPoolAction(
    "init-visitor-pool-btn",
    "/api/visitor-pool/initialize/",
    "fa-users-cog",
    (data) =>
      `Visitor Pool Initialized!\n\nReset: ${data.reset || 0} directories\nCreated: ${data.created} visitors\nTotal: ${data.total} slots\nFree: ${data.free} available`,
  );
}

// Fill all visitor slots to trigger read-only mode (Dev only)
async function fillVisitorSlots(): Promise<void> {
  await visitorPoolAction(
    "fill-visitor-slots-btn",
    "/api/visitor-pool/fill-slots/",
    "fa-user-lock",
    (data) =>
      `Visitor Slots Filled!\n\n${data.filled} slots filled.\n${data.message}`,
  );
}

// Free all visitor slots (Dev only)
async function freeVisitorSlots(): Promise<void> {
  await visitorPoolAction(
    "free-visitor-slots-btn",
    "/api/visitor-pool/free-slots/",
    "fa-user-check",
    (data) =>
      `Visitor Slots Freed!\n\n${data.freed} slots freed.\n${data.message}`,
  );
}

// Make functions available globally for onclick handlers in footer
(window as any).initVisitorPool = initVisitorPool;
(window as any).fillVisitorSlots = fillVisitorSlots;
(window as any).freeVisitorSlots = freeVisitorSlots;
