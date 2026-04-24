/** Event handlers for console terminal instances (file drop, right-click, nav keys). */

import { uploadFiles } from "../../utils/file-upload";

/** Navigation keys that xterm should handle — not the browser (prevents container scroll). */
const NAV_KEYS = [
  "ArrowUp",
  "ArrowDown",
  "ArrowLeft",
  "ArrowRight",
  "PageUp",
  "PageDown",
  "Home",
  "End",
];

/**
 * Prevent browser default for navigation keys inside xterm's custom key handler.
 * Call at the top of `attachCustomKeyEventHandler`. Returns `true` when the key
 * was a nav key (meaning: xterm should still process it, but browser scrolling
 * is suppressed). Returns `false` when the key is not a nav key.
 */
export function preventNavKeyDefault(ev: KeyboardEvent): boolean {
  if (
    ev.type === "keydown" &&
    !ev.altKey &&
    !ev.ctrlKey &&
    !ev.metaKey &&
    NAV_KEYS.includes(ev.key)
  ) {
    ev.preventDefault();
    return true;
  }
  return false;
}

interface WsHolder {
  ws: WebSocket | null;
}

export function setupFileDrop(el: HTMLElement, inst: WsHolder): void {
  el.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
    el.classList.add("drop-target");
  });
  el.addEventListener("dragleave", () => el.classList.remove("drop-target"));
  el.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation();
    el.classList.remove("drop-target");
    const dt = e.dataTransfer;
    if (!dt) return;
    if (dt.files && dt.files.length > 0) {
      void uploadFiles(dt.files).then((paths) => {
        if (inst.ws?.readyState === WebSocket.OPEN)
          inst.ws.send(paths.join(" "));
      });
      return;
    }
    const raw = dt.getData("text/plain") ?? "";
    const paths = raw.split(";").filter(Boolean);
    if (paths.length > 0 && inst.ws?.readyState === WebSocket.OPEN)
      inst.ws.send(paths.join(" "));
  });
}

export function setupRightClick(el: HTMLElement, inst: WsHolder): void {
  let count = 0;
  let timer: ReturnType<typeof setTimeout> | null = null;
  el.addEventListener("contextmenu", (e: MouseEvent) => {
    e.preventDefault();
    count++;
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      const n = Math.min(count, 4);
      count = 0;
      timer = null;
      if (inst.ws?.readyState === WebSocket.OPEN) {
        inst.ws.send(String(n));
        setTimeout(() => {
          if (inst.ws?.readyState === WebSocket.OPEN) inst.ws.send("\r");
        }, 500);
      }
    }, 400);
  });
}
