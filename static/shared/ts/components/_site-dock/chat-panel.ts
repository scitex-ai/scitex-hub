/**
 * Floating dock chat — the dock's Chat button opens a small chat panel over
 * the current page instead of navigating to /chat/.
 */

import {
  EMBED_THEME_MESSAGE,
  effectiveTheme,
  embedUrl,
  maximizedRect,
  panelRect,
  toggleMaximized,
} from "./chat-float";
import { trustedParentNavigationPath } from "./embed-navigation";

const OPEN_KEY = "stx-site-dock-chat-open";
const MAX_KEY = "stx-site-dock-chat-max";

export interface ChatPanelOptions {
  navigate?: (path: string) => void;
}

function readFlag(key: string): boolean {
  try {
    return window.sessionStorage.getItem(key) === "1";
  } catch {
    return false;
  }
}

function writeFlag(key: string, on: boolean): void {
  try {
    if (on) window.sessionStorage.setItem(key, "1");
    else window.sessionStorage.removeItem(key);
  } catch {
    /* storage unavailable: the panel just forgets */
  }
}

export function initChatPanel(
  dock: HTMLElement,
  options: ChatPanelOptions = {},
): void {
  const navigate =
    options.navigate ?? ((path: string) => window.location.assign(path));
  const toggle = dock.querySelector<HTMLElement>("[data-dock-chat-toggle]");
  const panel = document.querySelector<HTMLElement>("[data-dock-chat-panel]");
  const frame = panel?.querySelector<HTMLIFrameElement>(
    "[data-dock-chat-frame]",
  );
  if (!toggle || !panel || !frame) return;
  // On the full chat page itself the button keeps navigating (it is active).
  if (window.location.pathname.startsWith("/chat/")) return;
  if (panel.parentElement !== document.body) document.body.appendChild(panel);

  let maximized = readFlag(MAX_KEY);
  const maxBtn = panel.querySelector<HTMLElement>("[data-dock-chat-maximize]");
  // A user-dragged panel stays where dropped instead of following the dock;
  // reopening re-docks it. Resolves "should it move with the launcher":
  // it follows until you grab it.
  let userPlaced = false;

  const place = () => {
    if (panel.hidden || userPlaced) return;
    const r = dock.getBoundingClientRect();
    const rect = (maximized ? maximizedRect : panelRect)(
      { left: r.left, top: r.top, width: r.width, height: r.height },
      { width: window.innerWidth, height: window.innerHeight },
    );
    panel.style.left = `${rect.left}px`;
    panel.style.top = `${rect.top}px`;
    panel.style.width = `${rect.width}px`;
    panel.style.height = `${rect.height}px`;
  };

  const darkQuery = window.matchMedia?.("(prefers-color-scheme: dark)");
  const pageTheme = () =>
    effectiveTheme(
      document.documentElement.getAttribute("data-theme"),
      darkQuery?.matches ?? false,
    );
  const syncTheme = () => {
    frame.contentWindow?.postMessage(
      { type: EMBED_THEME_MESSAGE, theme: pageTheme() },
      window.location.origin,
    );
  };
  frame.addEventListener("load", syncTheme);
  new MutationObserver(syncTheme).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });
  darkQuery?.addEventListener?.("change", syncTheme);

  const resetFrame = () => frame.removeAttribute("src");
  const setOpen = (open: boolean) => {
    if (open) userPlaced = false; // reopening re-docks the panel
    if (open && !frame.getAttribute("src")) {
      frame.src = embedUrl(
        window.location.pathname,
        document.title,
        pageTheme(),
      );
    }
    panel.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    toggle.classList.toggle("is-active", open);
    writeFlag(OPEN_KEY, open);
    place();
  };

  const setMaximized = (on: boolean) => {
    maximized = on;
    panel.classList.toggle("is-maximized", on);
    if (maxBtn) {
      const label =
        (on ? maxBtn.dataset.labelRestore : maxBtn.dataset.labelMax) ?? "";
      maxBtn.setAttribute("aria-label", label);
      maxBtn.setAttribute("title", label);
    }
    writeFlag(MAX_KEY, on);
    place();
  };
  setMaximized(maximized);

  let navigationPending = false;
  window.addEventListener("message", (event) => {
    if (navigationPending) return;
    const target = trustedParentNavigationPath(
      event,
      frame.contentWindow,
      window.location.origin,
    );
    if (!target) return;
    navigationPending = true;
    setMaximized(false);
    setOpen(false);
    resetFrame();
    navigate(target);
  });
  // A top-level Back or a Settings Cancel may restore this page from bfcache.
  // Release the click guard and discard any stale nested iframe document.
  window.addEventListener("pageshow", () => {
    navigationPending = false;
    if (panel.hidden) resetFrame();
  });

  toggle.addEventListener("click", (e) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    e.preventDefault();
    setOpen(panel.hidden);
  });
  panel
    .querySelector("[data-dock-chat-minimize]")
    ?.addEventListener("click", () => setOpen(false));
  maxBtn?.addEventListener("click", () =>
    setMaximized(toggleMaximized(maximized)),
  );
  panel
    .querySelector("[data-dock-chat-close]")
    ?.addEventListener("click", () => {
      setMaximized(false);
      setOpen(false);
      resetFrame();
    });
  panel.addEventListener("keydown", (e) => {
    if (e.key === "Escape") setOpen(false);
  });

  // The head is a drag handle (PowerPoint-style, like the dock body):
  // dragging decouples the panel from the dock until reopened. Presses on
  // head buttons keep their own behaviour.
  const head = panel.querySelector<HTMLElement>(".site-dock-chat-head");
  head?.addEventListener("pointerdown", (down: PointerEvent) => {
    if (maximized) return;
    if (
      (down.target as HTMLElement | null)?.closest(
        "button,a,input,select,textarea,[contenteditable]",
      )
    )
      return;
    if (down.pointerType === "mouse" && down.button !== 0) return;
    down.preventDefault();
    const start = panel.getBoundingClientRect();
    const offsetX = down.clientX - start.left;
    const offsetY = down.clientY - start.top;
    let left = start.left;
    let top = start.top;
    let moved = false;
    try {
      head.setPointerCapture(down.pointerId);
    } catch {
      /* capture is best-effort */
    }
    const onMove = (e: PointerEvent) => {
      if (e.pointerId !== down.pointerId) return;
      if (
        !moved &&
        Math.hypot(e.clientX - down.clientX, e.clientY - down.clientY) < 7
      )
        return;
      if (!moved) {
        moved = true;
        userPlaced = true;
        panel.classList.add("site-dock-chat--dragging");
      }
      left = Math.min(
        Math.max(0, e.clientX - offsetX),
        window.innerWidth - start.width,
      );
      top = Math.min(
        Math.max(0, e.clientY - offsetY),
        window.innerHeight - start.height,
      );
      panel.style.left = `${left}px`;
      panel.style.top = `${top}px`;
    };
    const onUp = (e: PointerEvent) => {
      if (e.pointerId !== down.pointerId) return;
      head.removeEventListener("pointermove", onMove);
      head.removeEventListener("pointerup", onUp);
      head.removeEventListener("pointercancel", onUp);
      panel.classList.remove("site-dock-chat--dragging");
    };
    head.addEventListener("pointermove", onMove);
    head.addEventListener("pointerup", onUp);
    head.addEventListener("pointercancel", onUp);
  });

  // Follow the dock: dragging rewrites its inline left/top and class.
  new MutationObserver(place).observe(dock, {
    attributes: true,
    attributeFilter: ["style", "class"],
  });
  window.addEventListener("resize", place);

  if (readFlag(OPEN_KEY)) setOpen(true);
}
