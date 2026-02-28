/**
 * Input event handlers for PTY Terminal.
 * Keyboard shortcuts, right-click, clipboard, and file drop.
 */

/** Attach keyboard shortcut handler (clipboard, navigation, zen mode). */
export function attachKeyboardHandler(
  term: any,
  getWs: () => WebSocket | null,
): void {
  term.attachCustomKeyEventHandler((event: KeyboardEvent) => {
    // Global navigation shortcuts (Alt+key) - HIGHEST PRIORITY
    if (event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
      const key = event.key.toLowerCase();
      const navigationRoutes: Record<string, string> = {
        s: "/scholar/",
        v: "/vis/",
        w: "/writer/",
      };

      if (key === "z") {
        const zenEvent = new KeyboardEvent("keydown", {
          key: "F11",
          keyCode: 122,
          bubbles: true,
          cancelable: true,
        });
        document.dispatchEvent(zenEvent);
        return false;
      }

      if (key === "f") {
        const sidebarToggle = document.getElementById("sidebar-toggle");
        if (sidebarToggle) sidebarToggle.click();
        return false;
      }

      if (navigationRoutes[key]) {
        const route = navigationRoutes[key];
        if (!window.location.pathname.startsWith(route)) {
          window.location.href = route;
        }
        return false;
      }
    }

    // Ctrl+C: Copy selection or send SIGINT
    if (event.ctrlKey && (event.key === "C" || event.key === "c")) {
      const selection = term.getSelection();
      if (selection) {
        navigator.clipboard.writeText(selection);
        return false;
      }
      return true;
    }

    // Ctrl+V: Paste from clipboard
    if (event.ctrlKey && (event.key === "V" || event.key === "v")) {
      navigator.clipboard.readText().then((text: string) => {
        const ws = getWs();
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(text);
        }
      });
      return false;
    }

    return true;
  });
}

/** Attach right-click quick-selection handler (1-4 clicks). */
export function attachRightClickHandler(
  containerEl: HTMLElement,
  getWs: () => WebSocket | null,
): void {
  let rightClickCount = 0;
  let rightClickTimer: ReturnType<typeof setTimeout> | null = null;
  const RIGHT_CLICK_WINDOW = 400;

  containerEl.addEventListener("contextmenu", (e: MouseEvent) => {
    e.preventDefault();
    rightClickCount++;

    if (rightClickTimer) clearTimeout(rightClickTimer);

    rightClickTimer = setTimeout(() => {
      const count = Math.min(rightClickCount, 4);
      rightClickCount = 0;
      rightClickTimer = null;

      const ws = getWs();
      if (ws && ws.readyState === WebSocket.OPEN) {
        const digit = String(count);
        ws.send(digit);
        setTimeout(() => {
          const ws2 = getWs();
          if (ws2 && ws2.readyState === WebSocket.OPEN) {
            ws2.send("\r");
          }
        }, 500);
      }
    }, RIGHT_CLICK_WINDOW);
  });
}

/** Attach file drop handler for uploading OS files. */
export function attachFileDropHandler(
  containerEl: HTMLElement,
  getWs: () => WebSocket | null,
): void {
  containerEl.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
    containerEl.classList.add("drop-target");
  });
  containerEl.addEventListener("dragleave", () => {
    containerEl.classList.remove("drop-target");
  });
  containerEl.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation();
    containerEl.classList.remove("drop-target");
    const dt = e.dataTransfer;
    if (!dt) return;
    if (dt.files && dt.files.length > 0) {
      const csrf =
        document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
          ?.value ??
        (document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "");
      const form = new FormData();
      for (let i = 0; i < dt.files.length; i++)
        form.append("files", dt.files[i]);
      void fetch("/llm/api/upload/", {
        method: "POST",
        headers: { "X-CSRFToken": csrf },
        body: form,
      })
        .then((r) => r.json())
        .then((d: any) => {
          const ws = getWs();
          if (ws?.readyState === WebSocket.OPEN) ws.send(d.paths.join(" "));
        })
        .catch((err) => console.error("[PTY] Upload error:", err));
      return;
    }
    const raw = dt.getData("text/plain") ?? "";
    const paths = raw.split(";").filter(Boolean);
    const ws = getWs();
    if (paths.length > 0 && ws?.readyState === WebSocket.OPEN) {
      ws.send(paths.join(" "));
    }
  });
}
