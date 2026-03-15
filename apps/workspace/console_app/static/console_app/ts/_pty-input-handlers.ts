/**
 * Input event handlers for PTY Terminal.
 * Keyboard shortcuts, right-click, clipboard, file drop, and image paste.
 */

import { showPastePreview } from "./_paste-preview";
import { uploadFiles } from "./_upload-utils";

/** Show a brief thumbnail toast for pasted images (auto-dismiss). */
function showImageToast(blob: Blob, containerEl: HTMLElement): void {
  const url = URL.createObjectURL(blob);
  const toast = document.createElement("div");
  toast.className = "pty-image-toast";
  const img = document.createElement("img");
  img.src = url;
  const span = document.createElement("span");
  span.textContent = "Uploading\u2026";
  toast.appendChild(img);
  toast.appendChild(span);
  containerEl.appendChild(toast);
  setTimeout(() => {
    toast.remove();
    URL.revokeObjectURL(url);
  }, 2000);
}

/** Attach keyboard shortcut handler (clipboard, navigation, zen mode). */
export function attachKeyboardHandler(
  term: any,
  getWs: () => WebSocket | null,
  containerEl: HTMLElement,
  projectId: number,
): void {
  term.attachCustomKeyEventHandler((event: KeyboardEvent) => {
    // Global navigation shortcuts (Alt+key) - HIGHEST PRIORITY
    if (event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
      const key = event.key.toLowerCase();
      const navigationRoutes: Record<string, string> = {
        s: "/apps/scholar/",
        v: "/apps/figrecipe/",
        w: "/apps/writer/",
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
        const sidebarToggle = document.getElementById("stx-shell-sidebar__toggle");
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

    // Ctrl+V: Paste — check for images first, then fall back to text
    if (event.ctrlKey && (event.key === "V" || event.key === "v")) {
      navigator.clipboard
        .read()
        .then(async (items) => {
          for (const item of items) {
            const imageType = item.types.find((t: string) =>
              t.startsWith("image/"),
            );
            if (imageType) {
              const blob = await item.getType(imageType);
              const ext = imageType.split("/")[1] || "png";
              const file = new File([blob], `clipboard.${ext}`, {
                type: imageType,
              });
              showImageToast(blob, containerEl);
              try {
                const paths = await uploadFiles([file], projectId);
                const ws = getWs();
                if (ws?.readyState === WebSocket.OPEN) ws.send(paths.join(" "));
              } catch (err) {
                console.error("[PTY] Clipboard image upload error:", err);
              }
              return;
            }
          }
          // No image — text paste
          const text = await navigator.clipboard.readText();
          const ws = getWs();
          if (ws && ws.readyState === WebSocket.OPEN) ws.send(text);
        })
        .catch(() => {
          // clipboard.read() not supported or denied — fall back to text
          navigator.clipboard.readText().then((text: string) => {
            const ws = getWs();
            if (ws && ws.readyState === WebSocket.OPEN) ws.send(text);
          });
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

/** Attach file drop handler — uploads to scitex/downloads/. */
export function attachFileDropHandler(
  containerEl: HTMLElement,
  getWs: () => WebSocket | null,
  projectId: number,
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
  containerEl.addEventListener("drop", async (e) => {
    e.preventDefault();
    e.stopPropagation();
    containerEl.classList.remove("drop-target");
    const dt = e.dataTransfer;
    if (!dt) return;

    if (dt.files && dt.files.length > 0) {
      const files = Array.from(dt.files);
      // Show preview for image files
      const hasImages = files.some((f) => f.type.startsWith("image/"));
      if (hasImages) {
        const confirmed = await showPastePreview(files[0], containerEl);
        if (!confirmed) return;
      }

      try {
        const paths = await uploadFiles(files, projectId);
        const ws = getWs();
        if (ws?.readyState === WebSocket.OPEN) ws.send(paths.join(" "));
      } catch (err) {
        console.error("[PTY] Upload error:", err);
      }
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

/** Attach clipboard paste handler for images/files. */
export function attachClipboardPasteHandler(
  containerEl: HTMLElement,
  getWs: () => WebSocket | null,
  projectId: number,
): void {
  containerEl.addEventListener("paste", async (e: ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type.startsWith("image/") || item.kind === "file") {
        e.preventDefault();
        const file = item.getAsFile();
        if (!file) continue;

        // Generate a meaningful filename for clipboard images
        const ext = file.type.split("/")[1] || "png";
        const namedFile =
          file.name && file.name !== "image.png"
            ? file
            : new File([file], `clipboard.${ext}`, { type: file.type });

        const confirmed = await showPastePreview(namedFile, containerEl);
        if (!confirmed) return;

        try {
          const paths = await uploadFiles([namedFile], projectId);
          const ws = getWs();
          if (ws?.readyState === WebSocket.OPEN) ws.send(paths.join(" "));
        } catch (err) {
          console.error("[PTY] Clipboard upload error:", err);
        }
        return;
      }
    }
    // Text paste falls through to xterm's default handler
  });
}
