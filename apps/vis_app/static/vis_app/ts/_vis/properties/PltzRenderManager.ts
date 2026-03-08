/**
 * PltzRenderManager - Handles pltz bundle rendering and auto-update logic
 *
 * Extracted from PropertiesManager to reduce file size and improve modularity.
 */

import { getCSRFToken } from "../canvas/CanvasSerializationUtils";

export type RenderStatus =
  | "idle"
  | "pending"
  | "rendering"
  | "success"
  | "error";

export class PltzRenderManager {
  private csrfToken: string;

  // Debounce timers for auto-render per panel
  private renderDebounceTimers: Map<string, ReturnType<typeof setTimeout>> =
    new Map();

  // Track panels with pending changes (dirty flag)
  private dirtyPanels: Set<string> = new Set();

  // Auto-update interval in ms (configurable via dropdown)
  // 0 = Off, 500 = Hot, 1000 = Fast, 2000 = Normal, 5000 = Slow
  private autoUpdateInterval: number = 2000;

  // Callback for panel refresh after property changes
  private panelRefreshCallback?: (pltzPath: string) => Promise<void>;

  // Current pltz path for context
  private currentPltzPath: string | null = null;

  constructor() {
    this.csrfToken = getCSRFToken();
  }

  /**
   * Set the current pltz path
   */
  public setCurrentPltzPath(path: string | null): void {
    this.currentPltzPath = path;
  }

  /**
   * Get current pltz path
   */
  public getCurrentPltzPath(): string | null {
    return this.currentPltzPath;
  }

  /**
   * Set auto-update interval
   */
  public setAutoUpdateInterval(interval: number): void {
    this.autoUpdateInterval = interval;
    console.log(
      `[PltzRenderManager] Auto-update interval set to: ${interval}ms`,
    );
  }

  /**
   * Get auto-update interval
   */
  public getAutoUpdateInterval(): number {
    return this.autoUpdateInterval;
  }

  /**
   * Set callback for panel refresh after property changes
   */
  public setPanelRefreshCallback(
    callback: (pltzPath: string) => Promise<void>,
  ): void {
    this.panelRefreshCallback = callback;
  }

  /**
   * Mark panel as dirty and schedule auto-render
   */
  public markDirtyAndScheduleRender(pltzPath: string): void {
    this.dirtyPanels.add(pltzPath);
    this.showPendingStatus();
    this.scheduleAutoRender(pltzPath);
  }

  /**
   * Schedule debounced auto-render for a panel
   */
  private scheduleAutoRender(pltzPath: string): void {
    // Clear existing timer for this panel
    const existingTimer = this.renderDebounceTimers.get(pltzPath);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }

    // If auto-update is off, don't schedule render
    if (this.autoUpdateInterval === 0) {
      console.log(
        "[PltzRenderManager] Auto-update is off, skipping scheduled render",
      );
      return;
    }

    // Schedule new render
    const timer = setTimeout(async () => {
      if (this.dirtyPanels.has(pltzPath)) {
        console.log(
          `[PltzRenderManager] Auto-rendering panel after edits: ${pltzPath}`,
        );
        await this.renderAndRefreshPanel(pltzPath);
        this.dirtyPanels.delete(pltzPath);
      }
      this.renderDebounceTimers.delete(pltzPath);
    }, this.autoUpdateInterval);

    this.renderDebounceTimers.set(pltzPath, timer);
  }

  /**
   * Cancel pending auto-render for a panel
   */
  public cancelPendingRender(pltzPath?: string): void {
    if (pltzPath) {
      const timer = this.renderDebounceTimers.get(pltzPath);
      if (timer) {
        clearTimeout(timer);
        this.renderDebounceTimers.delete(pltzPath);
      }
      this.dirtyPanels.delete(pltzPath);
    } else {
      // Cancel all pending renders
      this.renderDebounceTimers.forEach((timer) => clearTimeout(timer));
      this.renderDebounceTimers.clear();
      this.dirtyPanels.clear();
    }
  }

  /**
   * Check if a panel has pending changes
   */
  public isPanelDirty(pltzPath: string): boolean {
    return this.dirtyPanels.has(pltzPath);
  }

  /**
   * Re-render pltz bundle and refresh canvas panel
   */
  public async renderAndRefreshPanel(pltzPath: string): Promise<void> {
    console.log("[PltzRenderManager] Re-rendering panel:", pltzPath);

    // Show rendering status
    this.updateRenderStatus("rendering");

    try {
      // Call render API
      const response = await fetch(
        `/apps/vis/api/bundles/pltz/render/?path=${encodeURIComponent(pltzPath)}`,
        {
          method: "POST",
          headers: {
            "X-CSRFToken": this.csrfToken,
          },
        },
      );

      if (!response.ok) {
        throw new Error("Failed to render pltz bundle");
      }

      // Call panel refresh callback if set
      if (this.panelRefreshCallback) {
        await this.panelRefreshCallback(pltzPath);
      }

      console.log("[PltzRenderManager] Panel re-rendered successfully");

      // Show success status briefly
      this.updateRenderStatus("success");
      setTimeout(() => this.updateRenderStatus("idle"), 2000);
    } catch (error) {
      console.error("[PltzRenderManager] Failed to re-render panel:", error);
      this.updateRenderStatus("error");
      setTimeout(() => this.updateRenderStatus("idle"), 3000);
    }
  }

  /**
   * Update render status UI
   */
  public updateRenderStatus(status: RenderStatus): void {
    const statusEl = document.getElementById("pltz-status");
    const refreshBtn = document.getElementById("pltz-refresh-btn");
    const refreshIcon = document.getElementById("pltz-refresh-icon");
    const refreshText = document.getElementById("pltz-refresh-text");

    if (!statusEl) return;

    switch (status) {
      case "idle":
        statusEl.style.display = "none";
        if (refreshBtn) refreshBtn.removeAttribute("disabled");
        if (refreshIcon) refreshIcon.className = "fas fa-sync-alt";
        if (refreshText) refreshText.textContent = "Re-render Panel";
        break;

      case "pending":
        statusEl.style.display = "block";
        statusEl.style.background = "var(--warning-bg, #3d3d00)";
        statusEl.style.color = "var(--warning-color, #ffc107)";
        statusEl.innerHTML = '<i class="fas fa-clock"></i> Changes pending...';
        break;

      case "rendering":
        statusEl.style.display = "block";
        statusEl.style.background = "var(--info-bg, #1a3a4a)";
        statusEl.style.color = "var(--info-color, #17a2b8)";
        statusEl.innerHTML =
          '<i class="fas fa-spinner fa-spin"></i> Rendering...';
        if (refreshBtn) refreshBtn.setAttribute("disabled", "true");
        if (refreshIcon) refreshIcon.className = "fas fa-spinner fa-spin";
        if (refreshText) refreshText.textContent = "Rendering...";
        break;

      case "success":
        statusEl.style.display = "block";
        statusEl.style.background = "var(--success-bg, #1a3d1a)";
        statusEl.style.color = "var(--success-color, #28a745)";
        statusEl.innerHTML = '<i class="fas fa-check-circle"></i> Updated';
        if (refreshBtn) refreshBtn.removeAttribute("disabled");
        if (refreshIcon) refreshIcon.className = "fas fa-sync-alt";
        if (refreshText) refreshText.textContent = "Re-render Panel";
        break;

      case "error":
        statusEl.style.display = "block";
        statusEl.style.background = "var(--danger-bg, #3d1a1a)";
        statusEl.style.color = "var(--danger-color, #dc3545)";
        statusEl.innerHTML =
          '<i class="fas fa-exclamation-triangle"></i> Render failed';
        if (refreshBtn) refreshBtn.removeAttribute("disabled");
        if (refreshIcon) refreshIcon.className = "fas fa-sync-alt";
        if (refreshText) refreshText.textContent = "Retry Render";
        break;
    }
  }

  /**
   * Show pending status when edits are made
   */
  private showPendingStatus(): void {
    this.updateRenderStatus("pending");
  }
}
