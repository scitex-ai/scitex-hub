/**
 * Console Tab Manager for AI Panel
 *
 * Manages multiple terminal tabs in the console mode.
 * Follows the SessionsPanel chip-bar pattern but is purely client-side
 * (no backend persistence — terminals are ephemeral WebSocket connections).
 */

export interface ConsoleTab {
  id: string;
  name: string;
  sessionName: string;
  containerEl: HTMLElement;
}

const MAX_TABS = 5;

/** Get or create a persistent UUID for a terminal tab name */
function getSessionId(tabName: string): string {
  const key = `scitex-console-session-${tabName}`;
  let id = localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(key, id);
  }
  return id;
}

export class ConsoleTabManager {
  private tabs = new Map<string, ConsoleTab>();
  private activeTabId: string | null = null;
  private tabCounter = 0;
  private listEl: HTMLElement | null = null;
  private terminalHostEl: HTMLElement | null = null;
  private onSwitch: ((tab: ConsoleTab) => void) | null = null;
  private onCreate: ((tab: ConsoleTab) => void) | null = null;
  private onClose: ((tab: ConsoleTab) => void) | null = null;

  init(
    listEl: HTMLElement,
    terminalHostEl: HTMLElement,
    callbacks: {
      onSwitch: (tab: ConsoleTab) => void;
      onCreate: (tab: ConsoleTab) => void;
      onClose: (tab: ConsoleTab) => void;
    },
  ): void {
    this.listEl = listEl;
    this.terminalHostEl = terminalHostEl;
    this.onSwitch = callbacks.onSwitch;
    this.onCreate = callbacks.onCreate;
    this.onClose = callbacks.onClose;

    // New tab button
    const newBtn = this.listEl
      ?.closest(".scitex-ai-console-tabs-bar")
      ?.querySelector<HTMLButtonElement>(".scitex-ai-console-new-tab");
    newBtn?.addEventListener("click", () => this.createTab());
  }

  createTab(name?: string): ConsoleTab | null {
    if (this.tabs.size >= MAX_TABS) return null;

    this.tabCounter++;
    const id = `console-tab-${Date.now()}`;
    const tabName = name || `T${this.tabCounter}`;

    // Create a container div for this tab's terminal
    const containerEl = document.createElement("div");
    containerEl.className = "scitex-ai-console-terminal-instance";
    containerEl.dataset.tabId = id;
    containerEl.style.width = "100%";
    containerEl.style.height = "100%";
    containerEl.style.display = "none";
    this.terminalHostEl?.appendChild(containerEl);

    const sessionUuid = getSessionId(tabName);
    const sessionName = `ai-panel-${sessionUuid}`;
    const tab: ConsoleTab = { id, name: tabName, sessionName, containerEl };
    this.tabs.set(id, tab);
    this.onCreate?.(tab);
    this.switchTab(id);
    this.renderTabs();
    return tab;
  }

  switchTab(id: string): void {
    const tab = this.tabs.get(id);
    if (!tab) return;

    // Hide all tab containers
    for (const t of this.tabs.values()) {
      t.containerEl.style.display = "none";
    }
    // Show selected
    tab.containerEl.style.display = "block";
    this.activeTabId = id;
    this.onSwitch?.(tab);
    this.renderTabs();
  }

  closeTab(id: string): void {
    if (this.tabs.size <= 1) return; // Cannot close last tab

    const tab = this.tabs.get(id);
    if (!tab) return;

    // Switch to adjacent tab before closing
    if (this.activeTabId === id) {
      const keys = Array.from(this.tabs.keys());
      const idx = keys.indexOf(id);
      const nextId = keys[idx + 1] || keys[idx - 1];
      if (nextId) this.switchTab(nextId);
    }

    // Clean up localStorage for this tab's session UUID
    localStorage.removeItem(`scitex-console-session-${tab.name}`);

    this.onClose?.(tab);
    tab.containerEl.remove();
    this.tabs.delete(id);
    this.renumberTabs();
    this.renderTabs();
  }

  getActiveTab(): ConsoleTab | null {
    if (!this.activeTabId) return null;
    return this.tabs.get(this.activeTabId) || null;
  }

  getTabCount(): number {
    return this.tabs.size;
  }

  /** Renumber tabs T1..TN after a close, preserving session UUIDs */
  private renumberTabs(): void {
    let n = 1;
    for (const tab of this.tabs.values()) {
      const newName = `T${n}`;
      if (tab.name !== newName) {
        tab.name = newName;
      }
      n++;
    }
    this.tabCounter = this.tabs.size;
  }

  private renderTabs(): void {
    if (!this.listEl) return;
    this.listEl.innerHTML = "";

    for (const tab of this.tabs.values()) {
      const chip = document.createElement("div");
      chip.className = "scitex-ai-console-tab-item";
      if (tab.id === this.activeTabId) chip.classList.add("active");
      chip.dataset.tabId = tab.id;
      chip.title = tab.sessionName;

      const title = document.createElement("span");
      title.className = "scitex-ai-console-tab-title";
      title.textContent = tab.name;
      title.addEventListener("dblclick", (e) => {
        e.stopPropagation();
        this.startRename(chip, tab);
      });

      chip.appendChild(title);

      // Close button (only if more than 1 tab)
      if (this.tabs.size > 1) {
        const closeBtn = document.createElement("button");
        closeBtn.className = "scitex-ai-console-tab-close";
        closeBtn.innerHTML = '<i class="fas fa-times"></i>';
        closeBtn.title = "Close";
        closeBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          this.closeTab(tab.id);
        });
        chip.appendChild(closeBtn);
      }

      chip.addEventListener("click", () => this.switchTab(tab.id));
      this.listEl.appendChild(chip);
    }

    // Disable new-tab button if at limit
    const newBtn = this.listEl
      ?.closest(".scitex-ai-console-tabs-bar")
      ?.querySelector<HTMLButtonElement>(".scitex-ai-console-new-tab");
    if (newBtn) {
      newBtn.disabled = this.tabs.size >= MAX_TABS;
      newBtn.style.opacity = this.tabs.size >= MAX_TABS ? "0.4" : "";
    }
  }

  private startRename(chip: HTMLElement, tab: ConsoleTab): void {
    const titleEl = chip.querySelector(".scitex-ai-console-tab-title");
    if (!titleEl) return;

    const input = document.createElement("input");
    input.className = "scitex-ai-console-tab-rename";
    input.value = tab.name;
    titleEl.replaceWith(input);
    input.focus();
    input.select();

    const finish = () => {
      const val = input.value.trim() || tab.name;
      input.replaceWith(titleEl);
      titleEl.textContent = val;
      tab.name = val;
    };

    input.addEventListener("blur", finish);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        input.blur();
      } else if (e.key === "Escape") {
        input.value = tab.name;
        input.blur();
      }
    });
  }
}
