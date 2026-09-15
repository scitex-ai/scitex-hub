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

const OPEN_KEY = "stx-site-dock-chat-open";
const MAX_KEY = "stx-site-dock-chat-max";

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

export function initChatPanel(dock: HTMLElement): void {
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

  const place = () => {
    if (panel.hidden) return;
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

  const setOpen = (open: boolean) => {
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
    });
  panel.addEventListener("keydown", (e) => {
    if (e.key === "Escape") setOpen(false);
  });

  // Follow the dock: dragging rewrites its inline left/top and class.
  new MutationObserver(place).observe(dock, {
    attributes: true,
    attributeFilter: ["style", "class"],
  });
  window.addEventListener("resize", place);

  if (readFlag(OPEN_KEY)) setOpen(true);
}
