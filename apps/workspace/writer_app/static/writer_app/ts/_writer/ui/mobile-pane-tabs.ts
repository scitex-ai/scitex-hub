/**
 * Phone pane tabs (Editor / PDF / Details) and the "Opening manuscript" overlay.
 *
 * Below 768px the shared resizer auto-collapses the editor pane and lays the
 * PDF and Details panes side by side off-screen, so the phone showed only a
 * collapsed "Writer Editor" strip. Here one pane is shown at a time, chosen by
 * the server-rendered tabs (swipe on a non-editor area moves to a neighbour).
 */

const PHONE_QUERY = "(max-width: 767px)";
const PANES = ["editor", "pdf", "details"] as const;
type Pane = (typeof PANES)[number];

function monacoEditors(): any[] {
  const w = window as any;
  const editors = w.monaco?.editor?.getEditors?.() ?? [];
  return editors.length
    ? editors
    : w.writerMonacoEditor
      ? [w.writerMonacoEditor]
      : [];
}

function panelsFor(workspace: HTMLElement): HTMLElement[] {
  return Array.from(
    workspace.querySelectorAll<HTMLElement>(
      ".split-view .latex-panel, .split-view .preview-panel, .writer-details",
    ),
  );
}

function uncollapse(workspace: HTMLElement): void {
  for (const panel of panelsFor(workspace)) {
    if (panel.classList.contains("collapsed"))
      panel.classList.remove("collapsed");
    panel.style.removeProperty("width");
    panel.style.removeProperty("min-width");
    panel.style.removeProperty("flex");
  }
}

function relayout(): void {
  const phone = window.matchMedia(PHONE_QUERY).matches;
  for (const ed of monacoEditors()) {
    try {
      ed.updateOptions({ minimap: { enabled: !phone } });
      ed.layout();
    } catch {
      /* editor disposed */
    }
  }
}

function selectPane(workspace: HTMLElement, pane: Pane): void {
  workspace.dataset.mobilePane = pane;
  workspace
    .querySelectorAll<HTMLElement>(".writer-mobile-tab")
    .forEach((tab) => {
      const on = tab.dataset.pane === pane;
      tab.setAttribute("aria-selected", on ? "true" : "false");
      tab.tabIndex = on ? 0 : -1;
    });
  if (!window.matchMedia(PHONE_QUERY).matches) return;
  uncollapse(workspace);
  if (pane === "pdf") (window as any).switchRightPanel?.("pdf");
  requestAnimationFrame(relayout);
}

function bindSwipe(workspace: HTMLElement): void {
  let x0 = 0;
  let y0 = 0;
  let tracking = false;
  workspace.addEventListener(
    "touchstart",
    (e) => {
      const t = e.target as HTMLElement;
      tracking =
        e.touches.length === 1 &&
        window.matchMedia(PHONE_QUERY).matches &&
        !t.closest(
          ".monaco-editor, input, textarea, select, .section-selector-dropdown",
        );
      x0 = e.touches[0].clientX;
      y0 = e.touches[0].clientY;
    },
    { passive: true },
  );
  workspace.addEventListener(
    "touchend",
    (e) => {
      if (!tracking) return;
      tracking = false;
      const dx = e.changedTouches[0].clientX - x0;
      const dy = e.changedTouches[0].clientY - y0;
      if (Math.abs(dx) < 60 || Math.abs(dx) < 2 * Math.abs(dy)) return;
      const i = PANES.indexOf(
        (workspace.dataset.mobilePane as Pane) || "editor",
      );
      const next = PANES[i + (dx < 0 ? 1 : -1)];
      if (next) selectPane(workspace, next);
    },
    { passive: true },
  );
}

function watchLoading(): void {
  const overlay = document.getElementById("writer-loading-overlay");
  const host = document.getElementById("writer-monaco-editor");
  if (!overlay || !host) return;
  const ready = () =>
    host.querySelector(".monaco-editor, .writer-editor-error") ||
    host.closest(".latex-panel")?.querySelector(".writer-editor-error");
  const done = () => {
    overlay.hidden = true;
    observer.disconnect();
    relayout();
  };
  const observer = new MutationObserver(() => ready() && done());
  if (ready()) return done();
  observer.observe(host.closest(".latex-panel") || host, {
    childList: true,
    subtree: true,
  });
  window.setTimeout(done, 60000);
}

export function initMobilePaneTabs(): void {
  const workspace = document.querySelector<HTMLElement>(".writer-workspace");
  if (!workspace) return;
  watchLoading();
  workspace
    .querySelectorAll<HTMLElement>(".writer-mobile-tab")
    .forEach((tab) =>
      tab.addEventListener("click", () =>
        selectPane(workspace, tab.dataset.pane as Pane),
      ),
    );
  bindSwipe(workspace);

  // The shared resizers collapse panes on narrow screens during their own
  // init (and on later toggles); undo that while in phone mode.
  const observer = new MutationObserver(() => {
    if (window.matchMedia(PHONE_QUERY).matches) uncollapse(workspace);
  });
  for (const panel of panelsFor(workspace)) {
    observer.observe(panel, { attributes: true, attributeFilter: ["class"] });
  }
  const mq = window.matchMedia(PHONE_QUERY);
  mq.addEventListener?.("change", () => {
    if (mq.matches) uncollapse(workspace);
    relayout();
  });
  selectPane(workspace, (workspace.dataset.mobilePane as Pane) || "editor");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initMobilePaneTabs);
} else {
  initMobilePaneTabs();
}
