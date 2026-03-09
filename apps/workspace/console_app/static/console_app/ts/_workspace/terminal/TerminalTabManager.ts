/**
 * Terminal Tab Manager
 * Manages multiple terminal tabs similar to file tabs
 */

import { PTYTerminal } from "../../_pty-terminal";
import type { EditorConfig } from "../core/types";
import { modalManager } from "../ui/ModalManager";

interface TerminalTab {
  id: string;
  name: string;
  tmuxSession: string;
  terminal: PTYTerminal;
  containerElement: HTMLElement;
}

const SESSION_STORAGE_KEY = "scitex-terminal-tabs";

interface SavedTabState {
  tabs: Array<{ name: string; tmuxSession: string }>;
  activeSession: string;
  counter: number;
}

export class TerminalTabManager {
  private terminals: Map<string, TerminalTab> = new Map();
  private activeTerminalId: string | null = null;
  private config: EditorConfig;
  private terminalCounter: number = 1;
  private mainContainer: HTMLElement | null = null;
  private draggedTerminalId: string | null = null;

  constructor(config: EditorConfig) {
    this.config = config;
    this.mainContainer = document.getElementById("pty-terminal");
  }

  /**
   * Initialize — restore tabs from sessionStorage or create default.
   */
  async initialize(): Promise<void> {
    if (!this.mainContainer || !this.config.currentProject) {
      console.error("[TerminalTabManager] Container or project not found");
      return;
    }

    const saved = this.loadTabState();
    if (saved && saved.tabs.length > 0) {
      // Restore tabs from previous session (Ctrl+Shift+R)
      this.terminalCounter = saved.counter;
      for (const tab of saved.tabs) {
        await this.createTerminal(tab.name, tab.tmuxSession);
      }
      // Switch to previously active tab
      const activeTab = Array.from(this.terminals.values()).find(
        (t) => t.tmuxSession === saved.activeSession,
      );
      if (activeTab) this.switchTerminal(activeTab.id);
      console.log(
        `[TerminalTabManager] Restored ${saved.tabs.length} tabs from session`,
      );
    } else {
      // First time: create default terminal
      await this.createTerminal();
      console.log("[TerminalTabManager] Initialized with first terminal");
    }

    this.renderTabs();
  }

  /**
   * Create a new terminal tab
   * @param name Display name for the tab
   * @param tmuxSession tmux session name (e.g., "scitex-0"). Auto-generated if omitted.
   */
  async createTerminal(name?: string, tmuxSession?: string): Promise<string> {
    if (!this.mainContainer || !this.config.currentProject) {
      throw new Error("Container or project not found");
    }

    const terminalId = `terminal-${Date.now()}`;
    const tabIndex = this.terminalCounter++;
    const terminalName = name || `T${tabIndex}`;
    const sessionName = tmuxSession || `scitex-${tabIndex - 1}`;

    // Create container for this terminal
    const containerElement = document.createElement("div");
    containerElement.id = `${terminalId}-container`;
    containerElement.className = "terminal-instance";
    containerElement.style.cssText =
      "width: 100%; height: 100%; display: none;";

    this.mainContainer.appendChild(containerElement);

    // Create PTY terminal instance with tmux session name
    const terminal = new PTYTerminal(
      containerElement,
      this.config.currentProject.id,
      sessionName,
    );

    await terminal.waitForReady();

    // Store terminal tab
    this.terminals.set(terminalId, {
      id: terminalId,
      name: terminalName,
      tmuxSession: sessionName,
      terminal,
      containerElement,
    });

    // Switch to new terminal
    this.switchTerminal(terminalId);

    this.saveTabState();
    console.log(
      `[TerminalTabManager] Created terminal: ${terminalName} (${terminalId})`,
    );

    return terminalId;
  }

  /**
   * Switch to a different terminal tab
   */
  switchTerminal(terminalId: string): void {
    const terminal = this.terminals.get(terminalId);
    if (!terminal) {
      console.error(`[TerminalTabManager] Terminal not found: ${terminalId}`);
      return;
    }

    // Hide all terminals
    this.terminals.forEach((t) => {
      t.containerElement.style.display = "none";
    });

    // Show selected terminal
    terminal.containerElement.style.display = "block";
    this.activeTerminalId = terminalId;

    // Update tab UI
    this.renderTabs();

    // Focus the terminal
    terminal.terminal.focus();

    this.saveTabState();
    console.log(`[TerminalTabManager] Switched to: ${terminal.name}`);
  }

  /**
   * Close a terminal tab
   */
  closeTerminal(terminalId: string): void {
    const terminal = this.terminals.get(terminalId);
    if (!terminal) return;

    // Don't close if it's the last terminal
    if (this.terminals.size === 1) {
      console.warn("[TerminalTabManager] Cannot close the last terminal");
      return;
    }

    // If closing active terminal, switch to another
    if (this.activeTerminalId === terminalId) {
      const terminalIds = Array.from(this.terminals.keys());
      const currentIndex = terminalIds.indexOf(terminalId);
      const nextIndex = currentIndex > 0 ? currentIndex - 1 : currentIndex + 1;
      const nextTerminalId = terminalIds[nextIndex];

      if (nextTerminalId) {
        this.switchTerminal(nextTerminalId);
      }
    }

    // Clean up
    terminal.terminal.destroy();
    terminal.containerElement.remove();
    this.terminals.delete(terminalId);

    this.renderTabs();

    this.saveTabState();
    console.log(`[TerminalTabManager] Closed terminal: ${terminal.name}`);
  }

  /**
   * Rename a terminal tab
   */
  renameTerminal(terminalId: string, newName: string): void {
    const terminal = this.terminals.get(terminalId);
    if (!terminal) return;

    terminal.name = newName;
    this.renderTabs();

    this.saveTabState();
    console.log(`[TerminalTabManager] Renamed terminal to: ${newName}`);
  }

  /**
   * Start inline rename for a terminal tab
   */
  private startInlineRename(
    terminalId: string,
    labelElement: HTMLSpanElement,
    container: HTMLElement,
  ): void {
    const terminal = this.terminals.get(terminalId);
    if (!terminal) return;

    // Create input field
    const input = document.createElement("input");
    input.type = "text";
    input.value = terminal.name;
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

    // Replace label with input
    labelElement.style.display = "none";
    labelElement.parentElement?.insertBefore(input, labelElement);
    input.focus();
    input.select();

    const finishRename = () => {
      const newName = input.value.trim();
      if (newName && newName !== terminal.name) {
        this.renameTerminal(terminalId, newName);
      } else {
        // Restore original label
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
   * Get active terminal
   */
  getActiveTerminal(): PTYTerminal | null {
    if (!this.activeTerminalId) return null;

    const terminal = this.terminals.get(this.activeTerminalId);
    return terminal ? terminal.terminal : null;
  }

  /**
   * Switch to next terminal tab
   */
  switchToNextTab(): void {
    if (this.terminals.size <= 1) return;

    const terminalIds = Array.from(this.terminals.keys());
    const currentIndex = terminalIds.indexOf(this.activeTerminalId || "");
    const nextIndex = (currentIndex + 1) % terminalIds.length;

    this.switchTerminal(terminalIds[nextIndex]);
  }

  /**
   * Switch to previous terminal tab
   */
  switchToPrevTab(): void {
    if (this.terminals.size <= 1) return;

    const terminalIds = Array.from(this.terminals.keys());
    const currentIndex = terminalIds.indexOf(this.activeTerminalId || "");
    const prevIndex =
      (currentIndex - 1 + terminalIds.length) % terminalIds.length;

    this.switchTerminal(terminalIds[prevIndex]);
  }

  /**
   * Render terminal tabs in the UI
   */
  private renderTabs(): void {
    const tabsContainer = document.getElementById("terminal-tabs");
    if (!tabsContainer) return;

    // Clear existing tabs
    tabsContainer.innerHTML = "";

    // Render each tab
    this.terminals.forEach((terminal) => {
      const tab = document.createElement("button");
      tab.className = `terminal-tab ${terminal.id === this.activeTerminalId ? "active" : ""}`;
      tab.dataset.terminalId = terminal.id;
      tab.title = terminal.name;

      // Tab label
      const label = document.createElement("span");
      label.className = "terminal-tab-label";
      label.textContent = terminal.name;
      tab.appendChild(label);

      // Close button
      const closeBtn = document.createElement("span");
      closeBtn.className = "terminal-tab-close";
      closeBtn.innerHTML = "×";
      closeBtn.title = "Close terminal";
      closeBtn.onclick = async (e) => {
        e.stopPropagation();
        const confirmed = await modalManager.confirmClose(terminal.name);
        if (confirmed) this.closeTerminal(terminal.id);
      };
      tab.appendChild(closeBtn);

      // Tab click handler
      tab.onclick = () => {
        this.switchTerminal(terminal.id);
      };

      // Double-click to rename
      tab.ondblclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.startInlineRename(terminal.id, label, tabsContainer);
      };

      // Drag and drop reordering
      tab.draggable = true;
      tab.ondragstart = (e) => {
        this.draggedTerminalId = terminal.id;
        tab.classList.add("dragging");
        if (e.dataTransfer) {
          e.dataTransfer.effectAllowed = "move";
          e.dataTransfer.setData("text/plain", terminal.id);
        }
      };
      tab.ondragend = () => {
        this.draggedTerminalId = null;
        tab.classList.remove("dragging");
        // Remove all drag-over classes
        tabsContainer.querySelectorAll(".terminal-tab").forEach((t) => {
          t.classList.remove("drag-over");
        });
      };
      tab.ondragover = (e) => {
        e.preventDefault();
        if (this.draggedTerminalId && this.draggedTerminalId !== terminal.id) {
          tab.classList.add("drag-over");
        }
      };
      tab.ondragleave = () => {
        tab.classList.remove("drag-over");
      };
      tab.ondrop = (e) => {
        e.preventDefault();
        tab.classList.remove("drag-over");
        if (this.draggedTerminalId && this.draggedTerminalId !== terminal.id) {
          this.reorderTabs(this.draggedTerminalId, terminal.id);
        }
      };

      tabsContainer.appendChild(tab);
    });

    // Add "+" button at the end (inside scrollable container)
    const newTabBtn = document.createElement("button");
    newTabBtn.className = "terminal-tab-new";
    newTabBtn.innerHTML = "+";
    newTabBtn.title = "New terminal (Ctrl+Shift+T)";
    newTabBtn.onclick = () => {
      this.createTerminal();
    };
    tabsContainer.appendChild(newTabBtn);
  }

  /**
   * Update theme for all terminals
   */
  updateTheme(): void {
    this.terminals.forEach((terminal) => {
      terminal.terminal.updateTheme();
    });
  }

  /**
   * Reorder tabs by moving draggedId before targetId
   */
  private reorderTabs(draggedId: string, targetId: string): void {
    const entries = Array.from(this.terminals.entries());
    const draggedIndex = entries.findIndex(([id]) => id === draggedId);
    const targetIndex = entries.findIndex(([id]) => id === targetId);

    if (draggedIndex === -1 || targetIndex === -1) return;

    // Remove dragged entry
    const [draggedEntry] = entries.splice(draggedIndex, 1);

    // Calculate new target index (adjust if dragged was before target)
    const newTargetIndex =
      draggedIndex < targetIndex ? targetIndex - 1 : targetIndex;

    // Insert at new position
    entries.splice(newTargetIndex, 0, draggedEntry);

    // Rebuild the map (maintains new order)
    this.terminals.clear();
    entries.forEach(([id, terminal]) => {
      this.terminals.set(id, terminal);
    });

    this.renderTabs();
    this.saveTabState();
  }

  /**
   * Get total number of terminals
   */
  getTerminalCount(): number {
    return this.terminals.size;
  }

  /** Save tab state to sessionStorage (survives Ctrl+Shift+R). */
  private saveTabState(): void {
    const activeTab = this.activeTerminalId
      ? this.terminals.get(this.activeTerminalId)
      : null;
    const state: SavedTabState = {
      tabs: Array.from(this.terminals.values()).map((t) => ({
        name: t.name,
        tmuxSession: t.tmuxSession,
      })),
      activeSession: activeTab?.tmuxSession || "scitex-0",
      counter: this.terminalCounter,
    };
    try {
      sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(state));
    } catch {
      /* sessionStorage unavailable */
    }
  }

  /** Load tab state from sessionStorage. */
  private loadTabState(): SavedTabState | null {
    try {
      const raw = sessionStorage.getItem(SESSION_STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw) as SavedTabState;
    } catch {
      return null;
    }
  }
}
