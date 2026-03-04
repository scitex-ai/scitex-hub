/**
 * On-site page capture handler for agent-workspace interaction.
 * Listens for capture requests via terminal WebSocket control messages,
 * shows permission modal on first use, captures page, uploads screenshot.
 */

/** CSRF token helper */
function getCsrf(): string {
  return (
    document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
      ?.value ??
    (document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "")
  );
}

export interface CaptureRequest {
  action: "capture_request";
  request_id: string;
  project_id: string | number;
  message: string;
  needs_permission: boolean;
}

type PermissionScope = "project" | "global";

/** Load html2canvas dynamically (lazy load on first capture) */
let html2canvasLoaded: Promise<any> | null = null;
function loadHtml2Canvas(): Promise<any> {
  if (html2canvasLoaded) return html2canvasLoaded;
  html2canvasLoaded = new Promise((resolve, reject) => {
    if ((window as any).html2canvas) {
      resolve((window as any).html2canvas);
      return;
    }
    const script = document.createElement("script");
    script.src =
      "https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js";
    script.onload = () => resolve((window as any).html2canvas);
    script.onerror = () => reject(new Error("Failed to load html2canvas"));
    document.head.appendChild(script);
  });
  return html2canvasLoaded;
}

/** Show permission modal, returns user's choice */
function showPermissionModal(
  message: string,
  projectId: string | number,
): Promise<{ allowed: boolean; scope?: PermissionScope }> {
  return new Promise((resolve) => {
    // Remove existing modal
    const existing = document.querySelector(".on-site-permission-overlay");
    if (existing) existing.remove();

    const overlay = document.createElement("div");
    overlay.className = "on-site-permission-overlay";

    const modal = document.createElement("div");
    modal.className = "on-site-permission-modal";

    const title = document.createElement("h3");
    title.className = "on-site-permission-title";
    title.innerHTML = '<i class="fas fa-camera"></i> Page Capture Request';

    const desc = document.createElement("p");
    desc.className = "on-site-permission-desc";
    desc.textContent =
      message || "An agent wants to capture a screenshot of the current page.";

    const actions = document.createElement("div");
    actions.className = "on-site-permission-actions";

    const cleanup = () => overlay.remove();

    const makeBtn = (label: string, cls: string, onClick: () => void) => {
      const btn = document.createElement("button");
      btn.className = `on-site-permission-btn ${cls}`;
      btn.textContent = label;
      btn.onclick = () => {
        cleanup();
        onClick();
      };
      return btn;
    };

    actions.appendChild(
      makeBtn("Allow (this project)", "btn-project", () => {
        savePermission("project", "allow", projectId);
        resolve({ allowed: true, scope: "project" });
      }),
    );
    actions.appendChild(
      makeBtn("Allow (all projects)", "btn-global", () => {
        savePermission("global", "allow", projectId);
        resolve({ allowed: true, scope: "global" });
      }),
    );
    actions.appendChild(
      makeBtn("Deny", "btn-deny", () => {
        savePermission("project", "deny", projectId);
        resolve({ allowed: false });
      }),
    );

    modal.appendChild(title);
    modal.appendChild(desc);
    modal.appendChild(actions);
    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // ESC to deny
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        cleanup();
        document.removeEventListener("keydown", onKey);
        resolve({ allowed: false });
      }
    };
    document.addEventListener("keydown", onKey);
  });
}

/** Save permission preference to server */
async function savePermission(
  scope: PermissionScope,
  action: "allow" | "deny",
  projectId: string | number,
): Promise<void> {
  try {
    await fetch("/console/api/on-site/permission/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrf(),
      },
      body: JSON.stringify({ scope, action, project_id: projectId }),
    });
  } catch (err) {
    console.error("[OnSite] Failed to save permission:", err);
  }
}

/** Capture page and upload screenshot */
async function captureAndUpload(requestId: string): Promise<void> {
  try {
    const html2canvas = await loadHtml2Canvas();
    const canvas = await html2canvas(document.body, {
      useCORS: true,
      allowTaint: true,
      scale: 1,
      logging: false,
    });

    // Convert to base64 PNG
    const dataUrl = canvas.toDataURL("image/png");
    const base64 = dataUrl.split(",")[1];

    // Upload to server
    const resp = await fetch("/console/api/on-site/capture/upload/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrf(),
      },
      body: JSON.stringify({
        request_id: requestId,
        data: base64,
        format: "png",
      }),
    });

    if (!resp.ok) {
      console.error("[OnSite] Upload failed:", resp.status);
    } else {
      console.log("[OnSite] Capture uploaded for request:", requestId);
    }
  } catch (err) {
    console.error("[OnSite] Capture failed:", err);
  }
}

/** Handle incoming capture request from WebSocket control message */
export async function handleCaptureRequest(msg: CaptureRequest): Promise<void> {
  console.log("[OnSite] Capture request:", msg.request_id);

  if (msg.needs_permission) {
    const result = await showPermissionModal(msg.message, msg.project_id);
    if (!result.allowed) {
      console.log("[OnSite] Capture denied by user");
      // Notify server of denial
      try {
        await fetch("/console/api/on-site/capture/upload/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify({
            request_id: msg.request_id,
            denied: true,
          }),
        });
      } catch {
        /* best effort */
      }
      return;
    }
  }

  await captureAndUpload(msg.request_id);
}
