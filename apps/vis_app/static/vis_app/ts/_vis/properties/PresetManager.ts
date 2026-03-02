/**
 * PresetManager - Handles style preset operations
 *
 * Responsibilities:
 * - Load and save presets
 * - YAML configuration editing
 * - Unit conversion (mm/inch)
 * - Render editable defaults panel (delegated to EditableDefaultsBuilder)
 */

import { getCSRFToken } from "../canvas/CanvasSerializationUtils.js";
import { EditableDefaultsBuilder } from "./EditableDefaultsBuilder";

export interface PresetManagerCallbacks {
  updateDiagram: () => void;
  updateLivePreview: () => Promise<void>;
}

export class PresetManager {
  private csrfToken: string;
  private currentUnit: "mm" | "inch" = "mm";
  private currentPresetId: string | null = null;
  private presets: any[] = [];
  private currentDefaults: any = {};
  private previewDebounceTimer: number | null = null;
  private callbacks: PresetManagerCallbacks | null = null;

  constructor() {
    this.csrfToken = getCSRFToken();
  }

  public setCallbacks(callbacks: PresetManagerCallbacks): void {
    this.callbacks = callbacks;
  }

  public getCurrentDefaults(): any {
    return this.currentDefaults;
  }

  public getCurrentUnit(): "mm" | "inch" {
    return this.currentUnit;
  }

  /**
   * Initialize preset-related event handlers
   */
  public initPresetHandlers(): void {
    document.querySelectorAll(".unit-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const target = e.currentTarget as HTMLElement;
        const unit = target.getAttribute("data-unit") as "mm" | "inch";
        this.switchUnit(unit);
      });
    });

    const presetSelector = document.getElementById(
      "preset-selector",
    ) as HTMLSelectElement;
    if (presetSelector) {
      presetSelector.addEventListener("change", () => {
        this.switchPreset(presetSelector.value);
      });
    }

    document
      .getElementById("preset-save-btn")
      ?.addEventListener("click", () => this.savePresetAs());
    document
      .getElementById("preset-import-btn")
      ?.addEventListener("click", () => this.importYAML());
    document
      .getElementById("preset-export-btn")
      ?.addEventListener("click", () => this.exportYAML());
    document
      .getElementById("preset-apply-btn")
      ?.addEventListener("click", () => this.applyYAMLChanges());
  }

  /**
   * Load and display SCITEX_STYLE defaults
   */
  public async loadDefaultsTab(): Promise<void> {
    try {
      await this.loadPresets();

      const response = await fetch("/vis/api/style-presets/active/");
      const data = await response.json();

      if (data.style) {
        this.currentDefaults = data.style;
        this.updateYAMLTextarea();
        if (this.callbacks?.updateLivePreview) {
          await this.callbacks.updateLivePreview();
        }
      }
    } catch (error) {
      console.error("[PresetManager] Failed to load defaults:", error);
      const statusEl = document.getElementById("yaml-status");
      if (statusEl) {
        statusEl.className = "yaml-status error";
        statusEl.innerHTML =
          '<i class="fas fa-exclamation-triangle"></i> Failed to load defaults';
      }
    }
  }

  private async loadPresets(): Promise<void> {
    try {
      const response = await fetch("/vis/api/style-presets/");
      const data = await response.json();

      this.presets = data.presets || [];
      this.currentPresetId = data.active_preset_id;

      const selector = document.getElementById(
        "preset-selector",
      ) as HTMLSelectElement;
      if (selector) {
        selector.innerHTML = '<option value="">SciTeX Default</option>';
        this.presets.forEach((preset) => {
          const option = document.createElement("option");
          option.value = preset.id;
          option.textContent = preset.name;
          if (preset.id === this.currentPresetId) option.selected = true;
          selector.appendChild(option);
        });
      }
    } catch (error) {
      console.error("[PresetManager] Failed to load presets:", error);
    }
  }

  private async switchPreset(presetId: string): Promise<void> {
    try {
      if (!presetId) {
        const response = await fetch("/vis/api/editor/style/");
        const data = await response.json();
        this.currentDefaults = data.defaults;
        this.currentPresetId = null;
      } else {
        const response = await fetch(`/vis/api/style-presets/${presetId}/`);
        const data = await response.json();
        this.currentDefaults = data.merged_style;
        this.currentPresetId = presetId;

        await fetch(`/vis/api/style-presets/${presetId}/activate/`, {
          method: "POST",
          headers: { "X-CSRFToken": this.csrfToken },
        });
      }

      this.updateYAMLTextarea();
      const defaultsContent = document.getElementById("defaults-content");
      if (defaultsContent) {
        this.renderEditableDefaults(defaultsContent, this.currentDefaults);
      }
    } catch (error) {
      console.error("[PresetManager] Failed to switch preset:", error);
    }
  }

  private switchUnit(unit: "mm" | "inch"): void {
    this.currentUnit = unit;

    document.querySelectorAll(".unit-btn").forEach((btn) => {
      btn.classList.remove("active");
      if (btn.getAttribute("data-unit") === unit) btn.classList.add("active");
    });

    const defaultsContent = document.getElementById("defaults-content");
    if (defaultsContent) {
      this.renderEditableDefaults(defaultsContent, this.currentDefaults);
    }
  }

  private updateYAMLTextarea(): void {
    const textarea = document.getElementById(
      "preset-yaml-textarea",
    ) as HTMLTextAreaElement;
    if (!textarea) return;

    const sections = {
      "# Labels": ["title", "xlabel", "ylabel"],
      "# Axes Dimensions (mm)": [
        "axes_width_mm",
        "axes_height_mm",
        "axes_thickness_mm",
      ],
      "# Margins (mm)": [
        "margin_left_mm",
        "margin_right_mm",
        "margin_bottom_mm",
        "margin_top_mm",
      ],
      "# Font Sizes (pt)": [
        "axis_font_size_pt",
        "tick_font_size_pt",
        "title_font_size_pt",
        "legend_font_size_pt",
      ],
      "# Lines (mm)": ["trace_thickness_mm", "tick_length_mm", "tick_thickness_mm"],
      "# Output": ["dpi", "transparent", "auto_crop"],
    };

    let yaml = "# SciTeX Style Configuration\n\n";
    for (const [section, keys] of Object.entries(sections)) {
      yaml += `${section}\n`;
      for (const key of keys) {
        if (key in this.currentDefaults) {
          const value = this.currentDefaults[key];
          yaml +=
            typeof value === "string"
              ? `${key}: "${value}"\n`
              : `${key}: ${value}\n`;
        }
      }
      yaml += "\n";
    }
    textarea.value = yaml;
  }

  private async applyYAMLChanges(): Promise<void> {
    const textarea = document.getElementById(
      "preset-yaml-textarea",
    ) as HTMLTextAreaElement;
    const statusEl = document.getElementById("yaml-status");
    if (!textarea) return;

    try {
      const parsed: any = {};
      for (const line of textarea.value.split("\n")) {
        const trimmed = line.trim();
        if (trimmed.startsWith("#") || !trimmed) continue;

        const match = trimmed.match(/^(\w+):\s*(.+)$/);
        if (match) {
          let value: any = match[2].trim();
          if (value.startsWith('"') && value.endsWith('"'))
            value = value.slice(1, -1);
          else if (!isNaN(parseFloat(value))) value = parseFloat(value);
          if (value === "true") value = true;
          else if (value === "false") value = false;
          parsed[match[1]] = value;
        }
      }

      this.currentDefaults = { ...this.currentDefaults, ...parsed };
      this.updateDiagramTextBoxes();

      if (this.callbacks?.updateLivePreview)
        await this.callbacks.updateLivePreview();

      if (statusEl) {
        statusEl.className = "yaml-status success";
        statusEl.innerHTML =
          '<i class="fas fa-check-circle"></i> Applied successfully!';
        setTimeout(() => {
          statusEl.className = "yaml-status";
          statusEl.innerHTML =
            '<i class="fas fa-info-circle"></i> Edit YAML and click Apply to update preview';
        }, 3000);
      }
    } catch (error) {
      console.error("[PresetManager] YAML parse error:", error);
      if (statusEl) {
        statusEl.className = "yaml-status error";
        statusEl.innerHTML = `<i class="fas fa-exclamation-triangle"></i> Parse error: ${error}`;
      }
    }
  }

  private updateDiagramTextBoxes(): void {
    const titleInput = document.getElementById(
      "diagram-title-input",
    ) as HTMLInputElement;
    const xlabelInput = document.getElementById(
      "diagram-xlabel-input",
    ) as HTMLInputElement;
    const ylabelInput = document.getElementById(
      "diagram-ylabel-input",
    ) as HTMLInputElement;

    if (titleInput) titleInput.value = this.currentDefaults.title || "Title";
    if (xlabelInput)
      xlabelInput.value = this.currentDefaults.xlabel || "X Label";
    if (ylabelInput)
      ylabelInput.value = this.currentDefaults.ylabel || "Y Label";
  }

  private async savePresetAs(): Promise<void> {
    const name = prompt("Enter preset name:");
    if (!name) return;

    try {
      const response = await fetch("/vis/api/style-presets/create/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.csrfToken,
        },
        body: JSON.stringify({
          name,
          description: `Custom preset created ${new Date().toLocaleString()}`,
          style_config: this.currentDefaults,
        }),
      });

      const data = await response.json();
      if (response.ok) {
        alert(`Preset "${name}" saved successfully!`);
        await this.loadPresets();
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (error) {
      console.error("[PresetManager] Failed to save preset:", error);
      alert("Failed to save preset");
    }
  }

  private importYAML(): void {
    const input = document.getElementById(
      "yaml-import-input",
    ) as HTMLInputElement;
    if (!input) return;

    input.onchange = async () => {
      if (!input.files?.length) return;

      const formData = new FormData();
      formData.append("file", input.files[0]);

      try {
        const response = await fetch("/vis/api/style-presets/import/", {
          method: "POST",
          headers: { "X-CSRFToken": this.csrfToken },
          body: formData,
        });

        const data = await response.json();
        if (response.ok) {
          alert(data.message);
          await this.loadPresets();
        } else {
          alert(`Error: ${data.error}`);
        }
      } catch (error) {
        console.error("[PresetManager] Failed to import YAML:", error);
        alert("Failed to import YAML file");
      }
    };
    input.click();
  }

  private async exportYAML(): Promise<void> {
    if (!this.currentPresetId) {
      alert("Please select a preset to export (SciTeX Default cannot be exported)");
      return;
    }

    try {
      const response = await fetch(
        `/vis/api/style-presets/${this.currentPresetId}/export/`,
        {
          method: "POST",
          headers: { "X-CSRFToken": this.csrfToken },
        },
      );

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download =
          response.headers
            .get("Content-Disposition")
            ?.split("filename=")[1]
            ?.replace(/"/g, "") || "preset.yaml";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      } else {
        const data = await response.json();
        alert(`Error: ${data.error}`);
      }
    } catch (error) {
      console.error("[PresetManager] Failed to export YAML:", error);
      alert("Failed to export YAML file");
    }
  }

  // Unit conversion methods
  public mmToInch(mm: number): number {
    return mm / 25.4;
  }

  public inchToMm(inch: number): number {
    return inch * 25.4;
  }

  public formatWithUnit(value: number, isSizeValue: boolean): string {
    if (!isSizeValue) return value.toString();
    if (this.currentUnit === "inch") return this.mmToInch(value).toFixed(2);
    return value.toFixed(2);
  }

  public formatKey(key: string): string {
    return key
      .replace(/_/g, " ")
      .replace(/\b\w/g, (char) => char.toUpperCase());
  }

  public updatePreviewDebounced(): void {
    if (this.previewDebounceTimer) clearTimeout(this.previewDebounceTimer);

    this.previewDebounceTimer = window.setTimeout(() => {
      if (this.callbacks?.updateLivePreview) this.callbacks.updateLivePreview();
    }, 1000);
  }

  /**
   * Render editable defaults panel using EditableDefaultsBuilder
   */
  public renderEditableDefaults(
    container: HTMLElement,
    defaults: Record<string, any>,
  ): void {
    const html = EditableDefaultsBuilder.buildHTML(defaults, {
      formatKey: (key) => this.formatKey(key),
      formatWithUnit: (value, isSizeValue) =>
        this.formatWithUnit(value, isSizeValue),
      getCurrentUnit: () => this.currentUnit,
      onValueChange: (key, value, isSize) => {
        if (typeof value === "boolean") {
          this.currentDefaults[key] = value;
        } else {
          let parsedValue: any = value;
          if (!isNaN(parseFloat(value))) {
            parsedValue = parseFloat(value);
            if (isSize && this.currentUnit === "inch") {
              parsedValue = this.inchToMm(parsedValue);
            }
          }
          this.currentDefaults[key] = parsedValue;
        }
        if (this.callbacks?.updateDiagram) this.callbacks.updateDiagram();
        this.updatePreviewDebounced();
      },
      onNavigate: () => {},
    });

    container.innerHTML = html;
    EditableDefaultsBuilder.setupListeners(container, {
      formatKey: (key) => this.formatKey(key),
      formatWithUnit: (value, isSizeValue) =>
        this.formatWithUnit(value, isSizeValue),
      getCurrentUnit: () => this.currentUnit,
      onValueChange: (key, value, isSize) => {
        if (typeof value === "boolean") {
          this.currentDefaults[key] = value;
        } else {
          let parsedValue: any = value;
          if (!isNaN(parseFloat(value))) {
            parsedValue = parseFloat(value);
            if (isSize && this.currentUnit === "inch") {
              parsedValue = this.inchToMm(parsedValue);
            }
          }
          this.currentDefaults[key] = parsedValue;
        }
        if (this.callbacks?.updateDiagram) this.callbacks.updateDiagram();
        this.updatePreviewDebounced();
      },
      onNavigate: () => {},
    });
  }
}
