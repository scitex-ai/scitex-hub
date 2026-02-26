/**
 * Centralized Keyboard Shortcuts for SciTeX
 *
 * Alt+A        — Toggle AI panel + focus chat input
 * Alt+T        — Cycle focus to next pane
 * Alt+Shift+T  — Cycle focus to previous pane
 * Alt+Right    — Focus next (right) pane
 * Alt+Left     — Focus previous (left) pane
 * Alt+Shift+Right — Collapse current pane rightward
 * Alt+Shift+Left  — Collapse current pane leftward
 * Ctrl+U       — Upload files to AI chat
 */

interface PaneInfo {
  el: HTMLElement;
  toggleBtn: HTMLElement | null;
  isCollapsed: () => boolean;
  toggle: () => void;
}

function getOrderedPanes(): PaneInfo[] {
  const panes: PaneInfo[] = [];

  // AI panel (leftmost)
  const aiPanel = document.getElementById("scitex-ai-panel");
  if (aiPanel) {
    const aiToggle =
      document.getElementById("scitex-ai-toggle") ??
      document.getElementById("scitex-ai-fab");
    panes.push({
      el: aiPanel,
      toggleBtn: aiToggle,
      isCollapsed: () => aiPanel.classList.contains("collapsed"),
      toggle: () => aiToggle?.click(),
    });
  }

  // Main content (center — never collapsible)
  const main = document.getElementById("main-content");
  if (main) {
    panes.push({
      el: main,
      toggleBtn: null,
      isCollapsed: () => false,
      toggle: () => {},
    });
  }

  // Workspace sidebar panels (right side) — detected via data-panel-resizer
  const resizers = document.querySelectorAll<HTMLElement>(
    "[data-panel-resizer]:not(#scitex-ai-resizer)",
  );
  for (const r of resizers) {
    const target = r.dataset.target;
    if (!target) continue;
    const panel = document.querySelector<HTMLElement>(target);
    if (!panel || panel === aiPanel) continue;

    const toggleId = r.dataset.toggleBtn;
    const toggleBtn = toggleId ? document.getElementById(toggleId) : null;
    panes.push({
      el: panel,
      toggleBtn,
      isCollapsed: () => panel.classList.contains("collapsed"),
      toggle: () => toggleBtn?.click(),
    });
  }

  return panes;
}

let focusedPaneIndex = -1;

function focusPane(pane: PaneInfo): void {
  const focusable = pane.el.querySelector<HTMLElement>(
    "textarea, input:not([type=hidden]), [tabindex]",
  );
  if (focusable) {
    focusable.focus();
  } else {
    pane.el.focus();
  }
}

function cyclePanes(direction: 1 | -1): void {
  const panes = getOrderedPanes();
  if (panes.length === 0) return;

  // Find current focus
  const active = document.activeElement as HTMLElement;
  let idx = panes.findIndex((p) => p.el.contains(active));
  if (idx < 0) idx = focusedPaneIndex >= 0 ? focusedPaneIndex : 0;

  const next = (idx + direction + panes.length) % panes.length;
  const target = panes[next];

  // Expand if collapsed
  if (target.isCollapsed()) target.toggle();

  focusedPaneIndex = next;
  focusPane(target);
}

function curtainCollapse(direction: "left" | "right"): void {
  const panes = getOrderedPanes();
  if (direction === "left") {
    // Collapse leftward: find rightmost expanded collapsible pane
    for (let i = panes.length - 1; i >= 0; i--) {
      if (panes[i].toggleBtn && !panes[i].isCollapsed()) {
        panes[i].toggle();
        return;
      }
    }
  } else {
    // Collapse rightward: find leftmost expanded collapsible pane
    for (let i = 0; i < panes.length; i++) {
      if (panes[i].toggleBtn && !panes[i].isCollapsed()) {
        panes[i].toggle();
        return;
      }
    }
  }
}

function toggleAIPanel(): void {
  const fab = document.getElementById("scitex-ai-fab");
  const toggle = document.getElementById("scitex-ai-toggle");
  const panel = document.getElementById("scitex-ai-panel");
  const input = document.getElementById(
    "scitex-ai-input",
  ) as HTMLTextAreaElement | null;
  const terminal = document.getElementById("scitex-ai-console-terminal");

  if (panel?.classList.contains("collapsed")) {
    // Expand panel and focus the active mode (chat input or console)
    (fab ?? toggle)?.click();
    setTimeout(() => {
      const isConsole = terminal?.closest(".scitex-ai-view.active");
      if (isConsole && (window as any).aiPanelConsole) {
        (window as any).aiPanelConsole.focus();
      } else {
        input?.focus();
      }
    }, 260);
  } else {
    // Panel is open — check if focus is already inside
    const hasFocus = panel?.contains(document.activeElement);
    if (hasFocus) {
      // Already focused inside panel → collapse it
      (fab ?? toggle)?.click();
    } else {
      // Focus is elsewhere → bring focus to panel
      const isConsole = terminal?.closest(".scitex-ai-view.active");
      if (isConsole && (window as any).aiPanelConsole) {
        (window as any).aiPanelConsole.focus();
      } else {
        input?.focus();
      }
    }
  }
}

function triggerFileUpload(): void {
  // Create a temporary file input
  const input = document.createElement("input");
  input.type = "file";
  input.multiple = true;
  input.style.display = "none";

  input.addEventListener("change", async () => {
    if (!input.files || input.files.length === 0) return;

    const form = new FormData();
    for (let i = 0; i < input.files.length; i++) {
      form.append("files", input.files[i]);
    }

    const csrf =
      document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
        ?.value ??
      (document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "");

    try {
      const resp = await fetch("/llm/api/upload/", {
        method: "POST",
        headers: { "X-CSRFToken": csrf },
        body: form,
      });
      if (!resp.ok) throw new Error(`Upload failed: ${resp.status}`);
      const data = (await resp.json()) as { paths: string[] };

      // Insert paths into chat input
      const chatInput = document.getElementById(
        "scitex-ai-input",
      ) as HTMLTextAreaElement | null;
      if (chatInput && data.paths.length > 0) {
        const label =
          data.paths.length === 1
            ? `Uploaded file: ${data.paths[0]}`
            : `Uploaded files:\n${data.paths.map((p) => `  ${p}`).join("\n")}`;
        const existing = chatInput.value.trim();
        chatInput.value = existing ? `${existing}\n${label}` : label;
        chatInput.focus();
      }
    } catch (err) {
      console.error("[Shortcuts] File upload error:", err);
    }

    input.remove();
  });

  document.body.appendChild(input);
  input.click();
}

export function initKeyboardShortcuts(): void {
  document.addEventListener("keydown", (e) => {
    // Ctrl+U — Upload files
    if (e.ctrlKey && !e.shiftKey && !e.altKey && e.key === "u") {
      e.preventDefault();
      triggerFileUpload();
      return;
    }

    // Alt+A — Toggle AI panel
    if (e.altKey && !e.ctrlKey && !e.shiftKey && e.key === "a") {
      e.preventDefault();
      toggleAIPanel();
      return;
    }

    // Alt+T — Cycle next pane
    if (e.altKey && !e.ctrlKey && !e.shiftKey && e.key === "t") {
      e.preventDefault();
      cyclePanes(1);
      return;
    }

    // Alt+Shift+T — Cycle previous pane
    if (e.altKey && !e.ctrlKey && e.shiftKey && e.key === "T") {
      e.preventDefault();
      cyclePanes(-1);
      return;
    }

    // Alt+Right — Focus next right pane
    if (e.altKey && !e.ctrlKey && !e.shiftKey && e.key === "ArrowRight") {
      e.preventDefault();
      cyclePanes(1);
      return;
    }

    // Alt+Left — Focus previous left pane
    if (e.altKey && !e.ctrlKey && !e.shiftKey && e.key === "ArrowLeft") {
      e.preventDefault();
      cyclePanes(-1);
      return;
    }

    // Alt+Shift+Right — Collapse rightward (curtain)
    if (e.altKey && !e.ctrlKey && e.shiftKey && e.key === "ArrowRight") {
      e.preventDefault();
      curtainCollapse("right");
      return;
    }

    // Alt+Shift+Left — Collapse leftward (curtain)
    if (e.altKey && !e.ctrlKey && e.shiftKey && e.key === "ArrowLeft") {
      e.preventDefault();
      curtainCollapse("left");
      return;
    }
  });

  console.log("[Shortcuts] Keyboard shortcuts initialized");
}
