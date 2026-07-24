/**
 * Terminal tab-strip renderer — pure DOM construction extracted from
 * TerminalTabManager (512-line cap). Builds the per-tab buttons, the
 * inline-rename input and the drag-and-drop wiring; all state changes
 * flow back through the callbacks. No terminal or Map state in here.
 */

/** Minimal view of a tab the strip needs to render. */
export interface TabView {
  id: string;
  name: string;
}

/** State-changing callbacks back into TerminalTabManager. */
export interface TabStripCallbacks {
  onSwitch(id: string): void;
  /** Close request — the manager owns the confirm dialog + teardown. */
  onCloseRequest(id: string): void;
  onRename(id: string, newName: string): void;
  onReorder(draggedId: string, targetId: string): void;
  onNew(): void;
}

/** Swap a tab label for an inline rename input; commit via onRename. */
function startInlineRename(
  tab: TabView,
  labelElement: HTMLSpanElement,
  onRename: (newName: string) => void,
): void {
  const input = document.createElement("input");
  input.type = "text";
  input.value = tab.name;
  input.className = "terminal-tab-rename-input";
  input.style.cssText = `
    width: 100px;
    padding: 2px 4px;
    font-size: 13px;
    border: 1px solid var(--workspace-icon-primary);
    border-radius: 3px;
    background: var(--workspace-bg-primary);
    color: var(--text-primary);
    outline: none;
  `;

  labelElement.style.display = "none";
  labelElement.parentElement?.insertBefore(input, labelElement);
  input.focus();
  input.select();

  const finishRename = () => {
    const newName = input.value.trim();
    if (newName && newName !== tab.name) {
      onRename(newName);
    } else {
      labelElement.style.display = "";
      input.remove();
    }
  };

  input.onblur = finishRename;
  input.onkeydown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      finishRename();
    } else if (e.key === "Escape") {
      e.preventDefault();
      labelElement.style.display = "";
      input.remove();
    }
  };
}

/**
 * Render the terminal tab strip (tabs + "+" button) into `tabsContainer`.
 * Clears any previous content. Drag state lives in this render pass —
 * a reorder triggers a re-render through the callbacks.
 */
export function renderTerminalTabs(
  tabsContainer: HTMLElement,
  tabs: TabView[],
  activeId: string | null,
  cb: TabStripCallbacks,
): void {
  tabsContainer.innerHTML = "";
  let draggedTerminalId: string | null = null;

  for (const view of tabs) {
    const tab = document.createElement("button");
    tab.className = `terminal-tab ${view.id === activeId ? "active" : ""}`;
    tab.dataset.terminalId = view.id;
    tab.title = view.name;

    const label = document.createElement("span");
    label.className = "terminal-tab-label";
    label.textContent = view.name;
    tab.appendChild(label);

    const closeBtn = document.createElement("span");
    closeBtn.className = "terminal-tab-close";
    closeBtn.innerHTML = "×";
    closeBtn.title = "Close terminal";
    closeBtn.onclick = (e) => {
      e.stopPropagation();
      cb.onCloseRequest(view.id);
    };
    tab.appendChild(closeBtn);

    tab.onclick = () => {
      cb.onSwitch(view.id);
    };

    tab.ondblclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      startInlineRename(view, label, (newName) =>
        cb.onRename(view.id, newName),
      );
    };

    // Drag and drop reordering
    tab.draggable = true;
    tab.ondragstart = (e) => {
      draggedTerminalId = view.id;
      tab.classList.add("dragging");
      if (e.dataTransfer) {
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", view.id);
      }
    };
    tab.ondragend = () => {
      draggedTerminalId = null;
      tab.classList.remove("dragging");
      tabsContainer.querySelectorAll(".terminal-tab").forEach((t) => {
        t.classList.remove("drag-over");
      });
    };
    tab.ondragover = (e) => {
      e.preventDefault();
      if (draggedTerminalId && draggedTerminalId !== view.id) {
        tab.classList.add("drag-over");
      }
    };
    tab.ondragleave = () => {
      tab.classList.remove("drag-over");
    };
    tab.ondrop = (e) => {
      e.preventDefault();
      tab.classList.remove("drag-over");
      if (draggedTerminalId && draggedTerminalId !== view.id) {
        cb.onReorder(draggedTerminalId, view.id);
      }
    };

    tabsContainer.appendChild(tab);
  }

  // "+" button at the end (inside scrollable container)
  const newTabBtn = document.createElement("button");
  newTabBtn.className = "terminal-tab-new";
  newTabBtn.innerHTML = "+";
  newTabBtn.title = "New terminal (Ctrl+Shift+T)";
  newTabBtn.onclick = () => {
    cb.onNew();
  };
  tabsContainer.appendChild(newTabBtn);
}
