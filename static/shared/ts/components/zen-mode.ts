/**
 * Zen Mode Component
 * Provides distraction-free mode by hiding header, sidebar, and details panels
 *
 * Features:
 * - F11 cycle: normal → zen → fullscreen → normal
 * - ESC: exit to previous state
 * - Remembers panel states before entering zen mode
 * - Restores panel states when exiting zen mode
 * - Works with existing WorkspacePanelResizer component
 *
 * Refactored: ZenPanelManager handles panel state capture/restore.
 */

import { ZenPanelManager, SavedPanelStates } from "./ZenPanelManager";

console.log("[DEBUG] shared/ts/components/zen-mode.ts loaded");

export interface ZenModeConfig {
  /** CSS selector for header element */
  headerSelector: string;
  /** CSS selector for sidebar panel */
  sidebarSelector?: string;
  /** CSS selector for details/right panel */
  detailsSelector?: string;
  /** ID of sidebar toggle button (for icon sync) */
  sidebarToggleId?: string;
  /** ID of details toggle button (for icon sync) */
  detailsToggleId?: string;
  /** localStorage key prefix */
  storagePrefix?: string;
}

// Re-export for backwards compatibility
export type { SavedPanelStates };

type ZenState = "normal" | "zen" | "fullscreen";

const ZEN_MODE_STORAGE_KEY = "scitex-zen-mode-active";
const ZEN_SAVED_STATES_KEY = "scitex-zen-saved-states";

// URL hash values for direct access (useful for screenshots/testing)
// e.g., /writer/#zen, /code/#fullscreen, /writer/#default
const HASH_ZEN = "zen";
const HASH_FULLSCREEN = "fullscreen";
const HASH_DEFAULT = "default";

export class ZenMode {
  private config: ZenModeConfig;
  private currentState: ZenState = "normal";
  private savedStates: SavedPanelStates | null = null;
  private initialized = false;
  private exitingToNormal = false;
  private panelManager: ZenPanelManager;

  constructor(config: ZenModeConfig) {
    this.config = {
      storagePrefix: "scitex-workspace-",
      ...config,
    };
    this.panelManager = new ZenPanelManager({
      headerSelector: this.config.headerSelector,
      sidebarSelector: this.config.sidebarSelector,
      detailsSelector: this.config.detailsSelector,
      sidebarToggleId: this.config.sidebarToggleId,
      detailsToggleId: this.config.detailsToggleId,
      storagePrefix: this.config.storagePrefix,
    });
  }

  /**
   * Initialize zen mode with keyboard shortcuts
   */
  public init(): void {
    if (this.initialized) return;
    this.initialized = true;

    // Check if we were in zen mode before page reload
    this.restoreZenState();

    // Set up keyboard shortcuts
    // Use capture phase to intercept F11 before the browser handles it
    document.addEventListener("keydown", this.handleKeyDown.bind(this), {
      capture: true,
    });

    // Listen for fullscreen changes (e.g., user presses browser's native F11)
    document.addEventListener(
      "fullscreenchange",
      this.handleFullscreenChange.bind(this),
    );

    console.log("[ZenMode] Initialized");
    console.log("[ZenMode] Shortcuts:");
    console.log(
      "  F11 or Alt+Z: Cycle through normal → zen → fullscreen → normal",
    );
    console.log("  ESC: Exit zen/fullscreen mode");
  }

  /**
   * Handle keyboard events
   */
  private handleKeyDown(e: KeyboardEvent): void {
    // F11: Cycle through states (keyCode 122 for browser compatibility)
    if (e.key === "F11" || e.keyCode === 122) {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      this.cycleState();
      return;
    }

    // Alt+Z: Alternative shortcut for zen mode toggle
    if (e.altKey && (e.key === "z" || e.key === "Z")) {
      e.preventDefault();
      e.stopPropagation();
      this.cycleState();
      return;
    }

    // ESC: Exit to previous state
    if (e.key === "Escape" || e.keyCode === 27) {
      if (this.currentState !== "normal") {
        e.preventDefault();
        this.exitToNormal();
      }
    }
  }

  /**
   * Cycle through states: normal → zen → fullscreen → normal
   */
  public cycleState(): void {
    switch (this.currentState) {
      case "normal":
        this.enterZenMode();
        break;
      case "zen":
        this.enterFullscreen();
        break;
      case "fullscreen":
        this.exitToNormal();
        break;
    }
  }

  /**
   * Enter zen mode (hide all panels)
   */
  public enterZenMode(): void {
    if (this.currentState === "zen" || this.currentState === "fullscreen")
      return;

    // Save current panel states before entering zen mode
    this.savedStates = this.panelManager.captureCurrentStates();
    this.persistSavedStates();

    // Add zen-mode class to body for CSS targeting
    document.body.classList.add("zen-mode");

    // Collapse all panels
    this.panelManager.collapseAllPanels();

    this.currentState = "zen";
    localStorage.setItem(ZEN_MODE_STORAGE_KEY, "zen");

    // Dispatch event for other components to react
    this.dispatchZenModeEvent("enter");

    // Show notification with shortcuts guide
    this.showNotification(
      "Zen mode – Press <kbd>F11</kbd> for fullscreen, <kbd>Esc</kbd> to exit",
    );

    console.log("[ZenMode] Entered zen mode");
  }

  /**
   * Enter fullscreen mode (zen + browser fullscreen)
   */
  public enterFullscreen(): void {
    if (this.currentState === "normal") {
      // If coming from normal, enter zen first
      this.enterZenMode();
    }

    // Request browser fullscreen
    const docEl = document.documentElement;
    if (docEl.requestFullscreen) {
      docEl.requestFullscreen().catch((err) => {
        console.warn("[ZenMode] Fullscreen request failed:", err);
      });
    }

    this.currentState = "fullscreen";
    localStorage.setItem(ZEN_MODE_STORAGE_KEY, "fullscreen");
    document.body.classList.add("zen-fullscreen");

    console.log("[ZenMode] Entered fullscreen mode");
  }

  /**
   * Exit zen mode and restore previous panel states
   */
  public exitToNormal(): void {
    // Set flag to prevent handleFullscreenChange from interfering
    this.exitingToNormal = true;

    // Exit browser fullscreen if active
    if (document.fullscreenElement) {
      document.exitFullscreen().catch((err) => {
        console.warn("[ZenMode] Exit fullscreen failed:", err);
      });
    }

    // Remove zen mode classes
    document.body.classList.remove("zen-mode", "zen-fullscreen");

    // Restore saved panel states
    if (this.savedStates) {
      this.panelManager.restorePanelStates(this.savedStates);
      this.savedStates = null;
      this.clearSavedStates();
    }

    this.currentState = "normal";
    localStorage.removeItem(ZEN_MODE_STORAGE_KEY);

    // Dispatch event for other components to react
    this.dispatchZenModeEvent("exit");

    console.log("[ZenMode] Exited to normal mode");

    // Reset flag after a short delay to allow fullscreenchange event to process
    setTimeout(() => {
      this.exitingToNormal = false;
    }, 100);
  }

  /**
   * Handle browser fullscreen change events
   */
  private handleFullscreenChange(): void {
    // Skip if we're intentionally exiting to normal mode
    if (this.exitingToNormal) {
      return;
    }

    if (!document.fullscreenElement && this.currentState === "fullscreen") {
      // User exited fullscreen via browser (e.g., native F11 or ESC)
      // Stay in zen mode but update state
      this.currentState = "zen";
      document.body.classList.remove("zen-fullscreen");
      localStorage.setItem(ZEN_MODE_STORAGE_KEY, "zen");
      console.log("[ZenMode] Exited fullscreen, staying in zen mode");
    }
  }

  /**
   * Persist saved states to localStorage (for page refresh)
   */
  private persistSavedStates(): void {
    if (this.savedStates) {
      localStorage.setItem(
        ZEN_SAVED_STATES_KEY,
        JSON.stringify(this.savedStates),
      );
    }
  }

  /**
   * Clear saved states from localStorage
   */
  private clearSavedStates(): void {
    localStorage.removeItem(ZEN_SAVED_STATES_KEY);
  }

  /**
   * Restore zen state on page load
   * Priority: URL hash > localStorage
   */
  private restoreZenState(): void {
    // Check URL hash first (e.g., /writer/#zen, /code/#fullscreen, /writer/#default)
    const hash = window.location.hash.slice(1).toLowerCase();

    // Handle #default hash - expand all panels, clear zen state
    if (hash === HASH_DEFAULT) {
      // Clear any zen mode state
      document.body.classList.remove("zen-mode", "zen-fullscreen");
      localStorage.removeItem(ZEN_MODE_STORAGE_KEY);
      localStorage.removeItem(ZEN_SAVED_STATES_KEY);
      this.currentState = "normal";
      this.savedStates = null;

      // Expand all panels
      this.panelManager.expandAllPanels();
      console.log("[ZenMode] Expanded all panels from URL hash #default");
      return;
    }

    if (hash === HASH_ZEN || hash === HASH_FULLSCREEN) {
      // Save current states before entering zen (for later restoration)
      this.savedStates = this.panelManager.captureCurrentStates();
      this.persistSavedStates();

      // Enter zen mode from URL hash
      document.body.classList.add("zen-mode");
      this.panelManager.collapseAllPanels();
      this.currentState = "zen";
      localStorage.setItem(ZEN_MODE_STORAGE_KEY, "zen");

      if (hash === HASH_FULLSCREEN) {
        // Note: Can't auto-enter fullscreen on page load due to browser restrictions
        console.log(
          "[ZenMode] Entered zen mode from URL hash (fullscreen requires user action)",
        );
      } else {
        console.log("[ZenMode] Entered zen mode from URL hash");
      }
      return;
    }

    // Fall back to localStorage
    const savedZenState = localStorage.getItem(ZEN_MODE_STORAGE_KEY);
    const savedStatesJson = localStorage.getItem(ZEN_SAVED_STATES_KEY);

    if (savedZenState && savedStatesJson) {
      try {
        this.savedStates = JSON.parse(savedStatesJson);
      } catch (e) {
        console.warn("[ZenMode] Failed to parse saved states:", e);
      }

      if (savedZenState === "zen" || savedZenState === "fullscreen") {
        // Re-enter zen mode after page load
        document.body.classList.add("zen-mode");
        this.panelManager.collapseAllPanels();
        this.currentState = "zen";

        if (savedZenState === "fullscreen") {
          // Note: Can't auto-enter fullscreen on page load due to browser restrictions
          // User will need to press F11 again for fullscreen
          console.log(
            "[ZenMode] Restored zen mode (fullscreen requires user action)",
          );
        } else {
          console.log("[ZenMode] Restored zen mode");
        }
      }
    }
  }

  /**
   * Set zen state programmatically (useful for testing/screenshots)
   * @param state - Target state: 'normal', 'zen', or 'fullscreen'
   */
  public setState(state: ZenState): void {
    switch (state) {
      case "normal":
        if (this.currentState !== "normal") {
          this.exitToNormal();
        }
        break;
      case "zen":
        if (this.currentState === "normal") {
          this.enterZenMode();
        } else if (this.currentState === "fullscreen") {
          // Exit fullscreen but stay in zen
          if (document.fullscreenElement) {
            document.exitFullscreen().catch(() => {});
          }
          this.currentState = "zen";
          document.body.classList.remove("zen-fullscreen");
        }
        break;
      case "fullscreen":
        this.enterFullscreen();
        break;
    }
  }

  /**
   * Show a notification message (like browser's fullscreen notification)
   */
  private showNotification(message: string, duration: number = 3000): void {
    // Remove existing notification if any
    const existing = document.querySelector(".zen-notification");
    if (existing) {
      existing.remove();
    }

    // Create notification element
    const notification = document.createElement("div");
    notification.className = "zen-notification";
    notification.innerHTML = message;
    document.body.appendChild(notification);

    // Trigger animation
    requestAnimationFrame(() => {
      notification.classList.add("visible");
    });

    // Auto-hide after duration
    setTimeout(() => {
      notification.classList.remove("visible");
      setTimeout(() => notification.remove(), 300);
    }, duration);
  }

  /**
   * Dispatch custom event for zen mode changes
   */
  private dispatchZenModeEvent(action: "enter" | "exit"): void {
    window.dispatchEvent(
      new CustomEvent("zen-mode-changed", {
        detail: {
          action,
          state: this.currentState,
          savedStates: this.savedStates,
        },
      }),
    );
  }

  /**
   * Get current zen mode state
   */
  public getState(): ZenState {
    return this.currentState;
  }

  /**
   * Check if zen mode is active
   */
  public isActive(): boolean {
    return this.currentState !== "normal";
  }
}

// Export singleton instance for global usage
export let zenModeInstance: ZenMode | null = null;

/**
 * Initialize zen mode with auto-detected configuration
 * Call this from workspace pages (writer, code, etc.)
 */
export function initZenMode(config?: Partial<ZenModeConfig>): ZenMode {
  const defaultConfig: ZenModeConfig = {
    headerSelector: ".global-header",
    sidebarSelector: config?.sidebarSelector,
    detailsSelector: config?.detailsSelector,
    sidebarToggleId: config?.sidebarToggleId,
    detailsToggleId: config?.detailsToggleId,
    storagePrefix: "scitex-workspace-",
  };

  zenModeInstance = new ZenMode({ ...defaultConfig, ...config });
  zenModeInstance.init();
  return zenModeInstance;
}

// Make available globally
if (typeof window !== "undefined") {
  (window as any).ZenMode = ZenMode;
  (window as any).initZenMode = initZenMode;
  // Expose getter for current instance (useful for testing/screenshots)
  Object.defineProperty(window, "zenMode", {
    get: () => zenModeInstance,
    configurable: true,
  });
}
