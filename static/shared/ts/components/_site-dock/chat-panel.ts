/**
 * Floating dock chat — the dock's Chat button opens a small chat panel over
 * the current page instead of navigating to /chat/.
 */

import { embedUrl, panelRect } from "./chat-float";

const OPEN_KEY = "stx-site-dock-chat-open";

function readOpen(): boolean {
  try {
    return window.sessionStorage.getItem(OPEN_KEY) === "1";
  } catch {
    return false;
  }
}

function writeOpen(open: boolean): void {
  try {
    if (open) window.sessionStorage.setItem(OPEN_KEY, "1");
    else window.sessionStorage.removeItem(OPEN_KEY);
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

  const place = () => {
    if (panel.hidden) return;
    const r = dock.getBoundingClientRect();
    const rect = panelRect(
      { left: r.left, top: r.top, width: r.width, height: r.height },
      { width: window.innerWidth, height: window.innerHeight },
    );
    panel.style.left = `${rect.left}px`;
    panel.style.top = `${rect.top}px`;
    panel.style.width = `${rect.width}px`;
    panel.style.height = `${rect.height}px`;
  };

  const setOpen = (open: boolean) => {
    if (open && !frame.getAttribute("src")) {
      frame.src = embedUrl(window.location.pathname, document.title);
    }
    panel.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    toggle.classList.toggle("is-active", open);
    writeOpen(open);
    place();
  };

  toggle.addEventListener("click", (e) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    e.preventDefault();
    setOpen(panel.hidden);
  });
  panel
    .querySelector("[data-dock-chat-close]")
    ?.addEventListener("click", () => setOpen(false));
  panel.addEventListener("keydown", (e) => {
    if (e.key === "Escape") setOpen(false);
  });

  // Follow the dock: dragging rewrites its inline left/top and class.
  new MutationObserver(place).observe(dock, {
    attributes: true,
    attributeFilter: ["style", "class"],
  });
  window.addEventListener("resize", place);

  if (readOpen()) setOpen(true);
}
