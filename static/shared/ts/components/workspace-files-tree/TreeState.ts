/**
 * Workspace Files Tree - State Management
 * Persists tree state (expanded folders, selection) to localStorage
 * Syncs state across browser tabs
 */

import type { TreeState, WorkspaceMode } from "./types.ts";

const STORAGE_KEY_PREFIX = "scitex_workspace_tree_";

export class TreeStateManager {
  private projectKey: string;
  private sharedKey: string; // For expanded paths (shared across modes)
  private mode: WorkspaceMode;
  private state: TreeState;
  private listeners: Set<(state: TreeState) => void> = new Set();

  constructor(username: string, slug: string, mode: WorkspaceMode = "all") {
    // Mode-specific key for selections (per-module)
    this.mode = mode;
    this.projectKey = `${STORAGE_KEY_PREFIX}${username}_${slug}_${mode}`;
    // Shared key for expanded paths (cross-module)
    this.sharedKey = `${STORAGE_KEY_PREFIX}${username}_${slug}_shared`;
    this.state = this.loadState();
    this.setupStorageListener();
  }

  /** Load state from localStorage */
  private loadState(): TreeState {
    let expandedPaths = new Set<string>();
    let selectedPath: string | null = null;
    let selectedPaths = new Set<string>();
    let targetPaths = new Set<string>();
    let scrollTop = 0;
    let focusPathPerMode = {
      console: null,
      vis: null,
      writer: null,
      scholar: null,
      verifier: null,
      hub: null,
      files: null,
      tools: null,
      explorer: null,
      all: null,
    };

    try {
      // Load expanded paths from shared storage (cross-module)
      const sharedStored = localStorage.getItem(this.sharedKey);
      if (sharedStored) {
        const sharedParsed = JSON.parse(sharedStored);
        expandedPaths = new Set(sharedParsed.expandedPaths || []);
      }
    } catch (err) {
      console.warn("[TreeState] Failed to load shared state:", err);
    }

    try {
      // Load mode-specific state (selections, targets, etc.)
      const stored = localStorage.getItem(this.projectKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        selectedPath = parsed.selectedPath || null;
        selectedPaths = new Set(parsed.selectedPaths || []);
        targetPaths = new Set(parsed.targetPaths || []);
        scrollTop = parsed.scrollTop || 0;
        focusPathPerMode = parsed.focusPathPerMode || focusPathPerMode;
      }
    } catch (err) {
      console.warn("[TreeState] Failed to load mode-specific state:", err);
    }

    return {
      expandedPaths,
      selectedPath,
      selectedPaths,
      targetPaths,
      scrollTop,
      focusPathPerMode,
      lastClickedPath: null, // Don't persist this
    };
  }

  /** Save state to localStorage */
  private saveState(): void {
    try {
      // Save expanded paths to shared storage (cross-module)
      const sharedSerializable = {
        expandedPaths: Array.from(this.state.expandedPaths),
      };
      localStorage.setItem(this.sharedKey, JSON.stringify(sharedSerializable));

      // Save mode-specific state (selections, targets, etc.)
      const serializable = {
        selectedPath: this.state.selectedPath,
        selectedPaths: Array.from(this.state.selectedPaths),
        targetPaths: Array.from(this.state.targetPaths),
        scrollTop: this.state.scrollTop,
        focusPathPerMode: this.state.focusPathPerMode,
        // lastClickedPath is not persisted
      };
      localStorage.setItem(this.projectKey, JSON.stringify(serializable));
    } catch (err) {
      console.warn("[TreeState] Failed to save state:", err);
    }
  }

  /** Listen for storage changes from other tabs */
  private setupStorageListener(): void {
    window.addEventListener("storage", (e) => {
      try {
        // Handle shared state changes (expanded paths)
        if (e.key === this.sharedKey && e.newValue) {
          const sharedParsed = JSON.parse(e.newValue);
          this.state.expandedPaths = new Set(sharedParsed.expandedPaths || []);
          this.notifyListeners();
        }
        // Handle mode-specific state changes (selections, targets, etc.)
        else if (e.key === this.projectKey && e.newValue) {
          const parsed = JSON.parse(e.newValue);
          this.state.selectedPath = parsed.selectedPath;
          this.state.selectedPaths = new Set(parsed.selectedPaths || []);
          this.state.targetPaths = new Set(parsed.targetPaths || []);
          this.state.scrollTop = parsed.scrollTop || 0;
          this.state.focusPathPerMode = parsed.focusPathPerMode || {
            console: null,
            vis: null,
            writer: null,
            scholar: null,
            verifier: null,
            hub: null,
            files: null,
            tools: null,
            explorer: null,
            all: null,
          };
          this.notifyListeners();
        }
      } catch (err) {
        console.warn("[TreeState] Failed to parse storage event:", err);
      }
    });
  }

  /** Notify all listeners of state change */
  private notifyListeners(): void {
    this.listeners.forEach((listener) => listener(this.state));
  }

  /** Subscribe to state changes */
  subscribe(listener: (state: TreeState) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /** Get current state */
  getState(): TreeState {
    return this.state;
  }

  /** Check if a path is expanded */
  isExpanded(path: string): boolean {
    return this.state.expandedPaths.has(path);
  }

  /** Expand a folder */
  expand(path: string): void {
    this.state.expandedPaths.add(path);
    this.saveState();
    this.notifyListeners();
  }

  /** Collapse a folder */
  collapse(path: string): void {
    this.state.expandedPaths.delete(path);
    this.saveState();
    this.notifyListeners();
  }

  /** Toggle folder expansion */
  toggle(path: string): boolean {
    const isExpanded = this.isExpanded(path);
    if (isExpanded) {
      this.collapse(path);
    } else {
      this.expand(path);
    }
    return !isExpanded;
  }

  /** Get all expanded paths */
  getExpanded(): Set<string> {
    return new Set(this.state.expandedPaths);
  }

  /** Set selected file path */
  setSelected(path: string | null): void {
    this.state.selectedPath = path;
    this.saveState();
    this.notifyListeners();
  }

  /** Get selected file path */
  getSelected(): string | null {
    return this.state.selectedPath;
  }

  // ===== Multi-Selection Methods =====

  /** Check if a path is in the multi-selection */
  isSelected(path: string): boolean {
    return this.state.selectedPaths.has(path);
  }

  /** Add path to multi-selection */
  addToSelection(path: string): void {
    this.state.selectedPaths.add(path);
    this.state.lastClickedPath = path;
    this.saveState();
    this.notifyListeners();
  }

  /** Remove path from multi-selection */
  removeFromSelection(path: string): void {
    this.state.selectedPaths.delete(path);
    this.saveState();
    this.notifyListeners();
  }

  /** Toggle path in multi-selection */
  toggleSelection(path: string): void {
    if (this.state.selectedPaths.has(path)) {
      this.state.selectedPaths.delete(path);
    } else {
      this.state.selectedPaths.add(path);
    }
    this.state.lastClickedPath = path;
    this.saveState();
    this.notifyListeners();
  }

  /** Get all selected paths */
  getSelectedPaths(): Set<string> {
    return new Set(this.state.selectedPaths);
  }

  /** Set multiple selected paths (replaces current selection) */
  setSelectedPaths(paths: string[]): void {
    this.state.selectedPaths = new Set(paths);
    this.saveState();
    this.notifyListeners();
  }

  /** Clear all multi-selection */
  clearSelection(): void {
    this.state.selectedPaths.clear();
    this.state.selectedPath = null;
    this.state.lastClickedPath = null;
    this.saveState();
    this.notifyListeners();
  }

  /** Get last clicked path for shift-click range selection */
  getLastClickedPath(): string | null {
    return this.state.lastClickedPath;
  }

  /** Set last clicked path */
  setLastClickedPath(path: string | null): void {
    this.state.lastClickedPath = path;
  }

  /** Select single item (clears multi-selection and sets single selection) */
  selectSingle(path: string): void {
    this.state.selectedPaths.clear();
    this.state.selectedPaths.add(path);
    this.state.selectedPath = path;
    this.state.lastClickedPath = path;
    this.saveState();
    this.notifyListeners();
  }

  /** Select single item without notifying listeners (for keyboard navigation) */
  selectSingleSilent(path: string): void {
    this.state.selectedPaths.clear();
    this.state.selectedPaths.add(path);
    this.state.selectedPath = path;
    this.state.lastClickedPath = path;
    this.saveState();
    // Do NOT notify listeners - caller will update UI directly
  }

  /** Set selected paths without notifying listeners (for keyboard navigation) */
  setSelectedPathsSilent(paths: string[]): void {
    this.state.selectedPaths = new Set(paths);
    this.saveState();
    // Do NOT notify listeners - caller will update UI directly
  }

  /** Set selected path without notifying listeners (for keyboard navigation) */
  setSelectedSilent(path: string | null): void {
    this.state.selectedPath = path;
    this.saveState();
    // Do NOT notify listeners - caller will update UI directly
  }

  // ===== End Multi-Selection Methods =====

  /** Update scroll position */
  setScrollTop(scrollTop: number): void {
    this.state.scrollTop = scrollTop;
    // Debounce scroll position saves
    this.saveState();
  }

  /** Get scroll position */
  getScrollTop(): number {
    return this.state.scrollTop;
  }

  /** Expand path to a file (expand all parent folders) */
  expandToPath(filePath: string): void {
    const parts = filePath.split("/");
    let currentPath = "";
    for (let i = 0; i < parts.length - 1; i++) {
      currentPath = currentPath ? `${currentPath}/${parts[i]}` : parts[i];
      this.state.expandedPaths.add(currentPath);
    }
    this.saveState();
    this.notifyListeners();
  }

  /** Check if a path is a target/active file */
  isTarget(path: string): boolean {
    return this.state.targetPaths.has(path);
  }

  /** Add a file to target/active files */
  addTarget(path: string): void {
    this.state.targetPaths.add(path);
    this.saveState();
    this.notifyListeners();
  }

  /** Remove a file from target/active files */
  removeTarget(path: string): void {
    this.state.targetPaths.delete(path);
    this.saveState();
    this.notifyListeners();
  }

  /** Set target files (replaces all current targets) */
  setTargets(paths: string[]): void {
    this.state.targetPaths = new Set(paths);
    this.saveState();
    this.notifyListeners();
  }

  /** Clear all target files */
  clearTargets(): void {
    this.state.targetPaths.clear();
    this.saveState();
    this.notifyListeners();
  }

  /** Get all target file paths */
  getTargets(): Set<string> {
    return new Set(this.state.targetPaths);
  }

  /** Set focus path for a specific mode */
  setFocusPath(
    mode: import("./types.js").WorkspaceMode,
    path: string | null,
  ): void {
    this.state.focusPathPerMode[mode] = path;
    this.saveState();
    this.notifyListeners();
  }

  /** Get focus path for a specific mode */
  getFocusPath(mode: import("./types.js").WorkspaceMode): string | null {
    return this.state.focusPathPerMode[mode];
  }

  /** Clear all state */
  clear(): void {
    this.state = {
      expandedPaths: new Set(),
      selectedPath: null,
      selectedPaths: new Set(),
      targetPaths: new Set(),
      scrollTop: 0,
      focusPathPerMode: {
        console: null,
        vis: null,
        writer: null,
        scholar: null,
        verifier: null,
        hub: null,
        files: null,
        tools: null,
        explorer: null,
        all: null,
      },
      lastClickedPath: null,
    };
    localStorage.removeItem(this.projectKey);
    localStorage.removeItem(this.sharedKey);
    this.notifyListeners();
  }
}
