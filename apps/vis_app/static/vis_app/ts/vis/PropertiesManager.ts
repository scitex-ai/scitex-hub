/**
 * PropertiesManager - Handles properties panel operations
 *
 * Responsibilities:
 * - Initialize properties panel tabs
 * - Switch between different property views (plot, format, layout, etc.)
 * - Update column dropdowns for plot configuration
 * - Manage properties panel state
 * - Coordinate pltz bundle property editing
 *
 * Delegates preset/style operations to PresetManager
 */

import { Dataset } from "./types.ts";
import { getCSRFToken } from "./canvas/CanvasSerializationUtils.ts";
import { CanvasObjectPropertiesBuilder } from "./properties/CanvasObjectPropertiesBuilder.ts";
import { ElementPropertiesBuilder } from "./properties/ElementPropertiesBuilder.ts";
import { PresetManager } from "./properties/PresetManager.js";
import { PreviewManager } from "./properties/PreviewManager.js";
import { PltzRenderManager } from "./properties/PltzRenderManager.ts";
import { PltzStatisticsManager } from "./properties/PltzStatisticsManager.ts";
import { PltzAnnotationsManager } from "./properties/PltzAnnotationsManager.ts";
import {
  DimensionsSection,
  StyleSection,
  LabelsSection,
  AxisTicksSection,
  TracesSection,
  LegendSection,
  ActionsSection,
} from "./properties/sections/index.ts";

export class PropertiesManager {
  private currentPropertiesTab: string = "plot";
  private csrfToken: string;

  // Plot property state
  private plotProperties = { lineWidth: 2, markerSize: 8 };

  // Reference to dynamic properties container
  private dynamicPropertiesEl: HTMLElement | null = null;
  private selectedItemInfoEl: HTMLElement | null = null;

  // Extracted managers - delegate preset operations
  private presetManager: PresetManager;
  private previewManager: PreviewManager;
  private renderManager: PltzRenderManager;
  private statisticsManager: PltzStatisticsManager;
  private annotationsManager: PltzAnnotationsManager;

  // Cache for pltz bundle data
  private pltzCache: Map<string, { spec: any; style: any; hash?: string }> =
    new Map();

  constructor(private getCurrentDataCallback?: () => Dataset | null) {
    this.dynamicPropertiesEl = document.getElementById("dynamic-properties");
    this.selectedItemInfoEl = document.querySelector(
      ".selected-item-info",
    ) as HTMLElement;
    this.csrfToken = getCSRFToken();

    // Initialize preset manager with callbacks
    this.presetManager = new PresetManager();

    // Initialize preview manager
    this.previewManager = new PreviewManager();
    this.previewManager.setCallbacks({
      getCurrentDefaults: () => this.presetManager.getCurrentDefaults(),
    });

    // Set preset manager callbacks for diagram/preview updates
    this.presetManager.setCallbacks({
      updateDiagram: () => {},
      updateLivePreview: () => this.previewManager.updateLivePreview(),
    });

    this.renderManager = new PltzRenderManager();
    this.statisticsManager = new PltzStatisticsManager();
    this.annotationsManager = new PltzAnnotationsManager();
    this.annotationsManager.setUpdatePropertyCallback((path, prop, val) =>
      this.updatePltzProperty(path, prop, val),
    );

    // Initialize handlers
    this.presetManager.initPresetHandlers();
    this.previewManager.initPreviewHandlers();
  }

  public getCurrentPropertiesTab(): string {
    return this.currentPropertiesTab;
  }

  public initPropertiesTabs(): void {
    const tabs = document.querySelectorAll(".properties-tab");
    if (tabs.length === 0) return;

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const tabName = tab.getAttribute("data-tab");
        if (!tabName) return;

        tabs.forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");

        const tabContents = document.querySelectorAll(
          ".properties-tab-content",
        );
        tabContents.forEach((content) => content.classList.remove("active"));

        const targetContent = document.getElementById(`tab-${tabName}`);
        if (targetContent) targetContent.classList.add("active");

        if (tabName === "defaults") this.presetManager.loadDefaultsTab();
        this.currentPropertiesTab = tabName;
        console.log(
          `[PropertiesManager] Switched to properties tab: ${tabName}`,
        );
      });
    });
    console.log("[PropertiesManager] Properties tabs initialized");
  }

  public setupPropertySliders(): void {
    document.querySelectorAll(".property-slider").forEach((slider) => {
      slider.addEventListener("input", (e) => {
        const target = e.target as HTMLInputElement;
        const valueSpan =
          target.parentElement?.querySelector(".property-value");
        if (valueSpan) valueSpan.textContent = target.value;
        if (target.id === "prop-line-width")
          this.plotProperties.lineWidth = parseInt(target.value);
        else if (target.id === "prop-marker-size")
          this.plotProperties.markerSize = parseInt(target.value);
      });
    });
  }

  public getPlotProperties(): { lineWidth: number; markerSize: number } {
    return { ...this.plotProperties };
  }

  public updateColumnDropdowns(): void {
    const currentData = this.getCurrentDataCallback?.();
    if (!currentData) return;

    const xColumnSelect = document.getElementById(
      "x-column",
    ) as HTMLSelectElement;
    const yColumnSelect = document.getElementById(
      "y-column",
    ) as HTMLSelectElement;
    if (xColumnSelect && yColumnSelect) {
      xColumnSelect.innerHTML = "";
      yColumnSelect.innerHTML = "";
      currentData.columns.forEach((col) => {
        xColumnSelect.add(new Option(col, col));
        yColumnSelect.add(new Option(col, col));
      });
      if (currentData.columns.length >= 2) {
        xColumnSelect.value = currentData.columns[0];
        yColumnSelect.value = currentData.columns[1];
      }
    }
  }

  public getSelectedColumns(): { xColumn: string; yColumn: string } {
    const xColumnSelect = document.getElementById(
      "x-column",
    ) as HTMLSelectElement;
    const yColumnSelect = document.getElementById(
      "y-column",
    ) as HTMLSelectElement;
    return {
      xColumn: xColumnSelect?.value || "",
      yColumn: yColumnSelect?.value || "",
    };
  }

  public setPropertiesCollapsed(collapsed: boolean): void {
    const propertiesPanel = document.querySelector(".sidebar-properties");
    if (propertiesPanel) {
      propertiesPanel.classList.toggle("collapsed", collapsed);
    }
  }

  public togglePropertiesPanel(): void {
    const propertiesPanel = document.querySelector(".sidebar-properties");
    if (propertiesPanel) {
      propertiesPanel.classList.toggle("collapsed");
    }
  }

  public switchToTab(tabName: string): void {
    const tabs = document.querySelectorAll("[data-props-tab]");
    const panels = document.querySelectorAll(".props-tab-panel");

    let targetTab: Element | null = null;
    tabs.forEach((tab) => {
      tab.classList.remove("active");
      if (tab.getAttribute("data-props-tab") === tabName) targetTab = tab;
    });
    if (targetTab) targetTab.classList.add("active");

    panels.forEach((panel) => panel.classList.remove("active"));
    const targetPanel = document.getElementById(`props-${tabName}`);
    if (targetPanel) targetPanel.classList.add("active");
  }

  public showPropertiesFor(
    elementType: string,
    elementLabel: string,
    elementData?: any,
  ): void {
    if (!this.dynamicPropertiesEl || !this.selectedItemInfoEl) return;

    this.updateSelectedItemInfo(elementType, elementLabel);
    const html = ElementPropertiesBuilder.buildElementPropertiesHTML(
      elementType,
      elementData,
    );
    this.dynamicPropertiesEl.innerHTML = html;
    console.log(`[PropertiesManager] Showing properties for: ${elementType}`);
  }

  private updateSelectedItemInfo(
    elementType: string,
    elementLabel: string,
  ): void {
    if (!this.selectedItemInfoEl) return;
    const headerEl = this.selectedItemInfoEl.querySelector(".selected-header");
    const labelEl = this.selectedItemInfoEl.querySelector(".selected-label");
    if (headerEl)
      headerEl.textContent =
        elementType.charAt(0).toUpperCase() + elementType.slice(1);
    if (labelEl) labelEl.textContent = elementLabel;
  }

  public showCanvasObjectProperties(obj: any): void {
    if (!this.dynamicPropertiesEl || !this.selectedItemInfoEl) return;
    if (obj.isBundlePanel && obj.pltzPath) {
      this.showPltzProperties(obj.pltzPath, obj.panelLabel || "A", obj);
      return;
    }
    const html = CanvasObjectPropertiesBuilder.build(obj);
    this.dynamicPropertiesEl.innerHTML = html;
  }

  public showNoSelection(): void {
    if (!this.dynamicPropertiesEl) return;
    this.dynamicPropertiesEl.innerHTML = `
            <div class="no-selection">
                <i class="fas fa-mouse-pointer"></i>
                <p>Select an element to view properties</p>
            </div>`;
  }

  public showElementProperties(elementName: string, elementInfo: any): void {
    if (!this.dynamicPropertiesEl || !this.selectedItemInfoEl) return;
    const label = elementInfo?.label || elementName;
    this.updateSelectedItemInfo("element", label);
    const html = ElementPropertiesBuilder.buildElementPropertiesHTML(
      elementName,
      elementInfo,
    );
    this.dynamicPropertiesEl.innerHTML = html;
  }

  public setPanelRefreshCallback(
    callback: (pltzPath: string) => Promise<void>,
  ): void {
    this.renderManager.setPanelRefreshCallback(callback);
  }

  /**
   * Show properties for a pltz bundle panel using section builders
   */
  public async showPltzProperties(
    pltzPath: string,
    panelLabel: string,
    obj: any,
  ): Promise<void> {
    if (!this.dynamicPropertiesEl || !this.selectedItemInfoEl) return;

    this.renderManager.setCurrentPltzPath(pltzPath);
    this.updateSelectedItemInfo("panel", `Panel ${panelLabel}`);
    this.dynamicPropertiesEl.innerHTML = `
            <div class="scitex-loading">
                <i class="fas fa-spinner fa-spin"></i> Loading pltz bundle...
            </div>`;

    try {
      const response = await fetch(
        `/vis/api/bundles/pltz/load/?path=${encodeURIComponent(pltzPath)}`,
      );
      if (!response.ok) throw new Error("Failed to load pltz bundle");

      const pltzData = await response.json();
      const spec = pltzData.spec || {};
      const style = pltzData.style || {};
      this.pltzCache.set(pltzPath, { spec, style });

      // Build HTML using section builders
      const html = [
        DimensionsSection.build(pltzPath, style),
        StyleSection.build(pltzPath, style),
        LabelsSection.build(pltzPath, spec),
        AxisTicksSection.build(pltzPath, spec, style),
        TracesSection.build(pltzPath, spec, style),
        LegendSection.build(pltzPath, style),
        ActionsSection.buildStatisticsSection(),
        ActionsSection.buildAnnotationsSection(),
        ActionsSection.buildButtonsSection(),
      ].join("");

      this.dynamicPropertiesEl.innerHTML = html;

      // Setup event listeners
      this.setupPltzPropertyListeners(pltzPath);
      this.setupAutoUpdateDropdown();
      this.annotationsManager.setup(pltzPath, spec?.annotations || []);
      this.statisticsManager.loadStatistics(pltzPath);
      this.statisticsManager.setupRefreshButton(pltzPath);

      console.log("[PropertiesManager] Showing pltz properties:", panelLabel);
    } catch (error) {
      console.error(
        "[PropertiesManager] Failed to load pltz properties:",
        error,
      );
      this.dynamicPropertiesEl.innerHTML = `
                <div class="scitex-error">
                    <i class="fas fa-exclamation-triangle"></i> Failed to load pltz bundle
                </div>`;
    }
  }

  private setupAutoUpdateDropdown(): void {
    const dropdown = document.getElementById(
      "pltz-auto-update-interval",
    ) as HTMLSelectElement;
    if (dropdown) {
      dropdown.value = String(this.renderManager.getAutoUpdateInterval());
      dropdown.addEventListener("change", () => {
        this.renderManager.setAutoUpdateInterval(parseInt(dropdown.value, 10));
      });
    }

    const updateNowBtn = document.getElementById("pltz-update-now-btn");
    if (updateNowBtn) {
      updateNowBtn.addEventListener("click", async () => {
        const path = this.renderManager.getCurrentPltzPath();
        if (path) await this.renderManager.renderAndRefreshPanel(path);
      });
    }

    const saveBtn = document.getElementById("pltz-save-btn");
    if (saveBtn) {
      saveBtn.addEventListener("click", () => {
        this.renderManager.updateRenderStatus("success");
        setTimeout(() => this.renderManager.updateRenderStatus("idle"), 2000);
      });
    }

    const resetBtn = document.getElementById("pltz-reset-btn");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        const path = this.renderManager.getCurrentPltzPath();
        if (path) {
          this.pltzCache.delete(path);
          console.log("[PropertiesManager] Reset pltz bundle");
        }
      });
    }
  }

  private setupPltzPropertyListeners(pltzPath: string): void {
    const editables =
      this.dynamicPropertiesEl?.querySelectorAll(".pltz-editable");
    if (!editables) return;

    editables.forEach((input) => {
      input.addEventListener("change", async (e) => {
        const target = e.target as HTMLInputElement | HTMLSelectElement;
        const property = target.dataset.property;
        const value =
          target.type === "checkbox"
            ? (target as HTMLInputElement).checked
            : target.value;
        if (property) await this.updatePltzProperty(pltzPath, property, value);
      });
    });
  }

  private async updatePltzProperty(
    pltzPath: string,
    property: string,
    value: any,
  ): Promise<void> {
    console.log(`[PropertiesManager] Updating: ${property} = ${value}`);

    const [type, ...pathParts] = property.split(".");
    if (type !== "spec" && type !== "style") return;

    const cached = this.pltzCache.get(pltzPath);
    if (!cached) return;

    // Update cached data locally for immediate UI feedback
    let obj = type === "spec" ? cached.spec : cached.style;
    for (let i = 0; i < pathParts.length - 1; i++) {
      const key = pathParts[i];
      if (obj[key] === undefined)
        obj[key] = isNaN(Number(pathParts[i + 1])) ? {} : [];
      obj = obj[key];
    }

    let parsedValue = value;
    if (value === "true") parsedValue = true;
    else if (value === "false") parsedValue = false;
    else if (!isNaN(Number(value)) && value !== "") parsedValue = Number(value);
    obj[pathParts[pathParts.length - 1]] = parsedValue;

    try {
      // Use new fine-grained property update endpoint
      const response = await fetch("/vis/api/bundles/pltz/update-property/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.csrfToken,
        },
        body: JSON.stringify({
          path: pltzPath,
          property_path: property,
          value: parsedValue,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to update property");
      }

      const result = await response.json();
      console.log(`[PropertiesManager] Property updated successfully:`, result);

      // Mark as dirty to trigger preview refresh
      this.renderManager.markDirtyAndScheduleRender(pltzPath);
    } catch (error) {
      console.error("[PropertiesManager] Update failed:", error);
      // Revert local cache on failure
      this.pltzCache.delete(pltzPath);
    }
  }

  public cancelPendingRender(pltzPath?: string): void {
    this.renderManager.cancelPendingRender(pltzPath);
  }

  public isPanelDirty(pltzPath: string): boolean {
    return this.renderManager.isPanelDirty(pltzPath);
  }
}
