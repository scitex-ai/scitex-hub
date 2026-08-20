/**
 * Terminal Tab Manager
 * Manages multiple terminal tabs similar to file tabs
 */

import { PTYTerminal } from "../../_pty-terminal";
import { showTerminalStartFailure } from "../../_pty-ui-helpers";
import type { EditorConfig } from "../core/types";
import { modalManager } from "../ui/ModalManager";
import { TerminalProviderPicker } from "./TerminalProviderPicker";
import { renderTerminalTabs } from "./TerminalTabStrip";

interface TerminalTab {
  id: string;
  name: string;
  tmuxSession: string;
  /** Model-provider id the session was created with ("" = default). */
  provider: string;
  terminal: PTYTerminal;
  containerElement: HTMLElement;
}

const SESSION_STORAGE_KEY = "scitex-terminal-tabs";

interface SavedTabState {
  tabs: Array<{ name: string; tmuxSession: string; provider?: string }>;
  activeSession: string;
  counter: number;
}

export class TerminalTabManager {
  private terminals: Map<string, TerminalTab> = new Map();
  private activeTerminalId: string | null = null;
  private config: EditorConfig;
  private terminalCounter: number = 1;
  private mainContainer: HTMLElement | null = null;
  private providerPicker: TerminalProviderPicker = new TerminalProviderPicker();

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

    await this.providerPicker.load();

    const saved = this.loadTabState();
    if (saved && saved.tabs.length > 0) {
      // Restore tabs from previous session (Ctrl+Shift+R)
      this.terminalCounter = saved.counter;
      for (const tab of saved.tabs) {
        // Old saved state has no provider field — restore as the server
        // default ("") rather than the current picker selection, so a
        // reattach never silently requests a different provider.
        await this.createTerminal(
          tab.name,
          tab.tmuxSession,
          tab.provider ?? "",
        );
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
   * @param provider Model-provider id ("" = default). New tabs pick up the
   *                 picker selection; restored tabs pass their saved value.
   */
  async createTerminal(
    name?: string,
    tmuxSession?: string,
    provider?: string,
  ): Promise<string> {
    if (!this.mainContainer || !this.config.currentProject) {
      throw new Error("Container or project not found");
    }

    const terminalId = `terminal-${Date.now()}`;
    const tabIndex = this.terminalCounter++;
    const terminalName = name || `T${tabIndex}`;
    const sessionName = tmuxSession || `scitex-${tabIndex - 1}`;
    const sessionProvider =
      provider ?? this.providerPicker.getSelectedProvider();

    // Create container for this terminal
    const containerElement = document.createElement("div");
    containerElement.id = `${terminalId}-container`;
    containerElement.className = "terminal-instance";
    containerElement.style.cssText =
      "width: 100%; height: 100%; display: none;";

    this.mainContainer.appendChild(containerElement);

    // Create PTY terminal instance with tmux session name. Fail LOUD:
    // if construction or initialization throws, the container must not
    // stay display:none with the failure visible only in the console —
    // un-hide it and render an explicit error state with a Retry button.
    let terminal: PTYTerminal;
    try {
      terminal = new PTYTerminal(
        containerElement,
        this.config.currentProject.id,
        sessionName,
        sessionProvider,
      );
      await terminal.waitForReady();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      containerElement.style.display = "block";
      showTerminalStartFailure(
        containerElement,
        `Terminal failed to start: ${message}`,
        () => {
          containerElement.remove();
          void this.createTerminal(terminalName, sessionName, sessionProvider);
        },
      );
      console.error(
        `[TerminalTabManager] Terminal failed to start: ${message}`,
        err,
      );
      throw err instanceof Error ? err : new Error(message);
    }

    // Store terminal tab
    this.terminals.set(terminalId, {
      id: terminalId,
      name: terminalName,
      tmuxSession: sessionName,
      provider: sessionProvider,
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
   * Render terminal tabs in the UI (DOM building lives in TerminalTabStrip)
   */
  private renderTabs(): void {
    const tabsContainer = document.getElementById("terminal-tabs");
    if (!tabsContainer) return;

    renderTerminalTabs(
      tabsContainer,
      Array.from(this.terminals.values()).map((t) => ({
        id: t.id,
        name: t.name,
      })),
      this.activeTerminalId,
      {
        onSwitch: (id) => this.switchTerminal(id),
        onCloseRequest: (id) => {
          const terminal = this.terminals.get(id);
          if (!terminal) return;
          void modalManager.confirmClose(terminal.name).then((confirmed) => {
            if (confirmed) this.closeTerminal(id);
          });
        },
        onRename: (id, newName) => this.renameTerminal(id, newName),
        onReorder: (draggedId, targetId) =>
          this.reorderTabs(draggedId, targetId),
        onNew: () => {
          void this.createTerminal();
        },
      },
    );

    // Model-provider picker for NEW sessions (Option A). Disabled with an
    // explanatory tooltip for readonly visitors; hidden when the registry
    // endpoint was unreachable.
    this.providerPicker.render(tabsContainer);
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
        provider: t.provider,
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
