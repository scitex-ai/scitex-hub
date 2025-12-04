/**
 * Compilation Settings Manager
 * Manages compilation preferences with localStorage persistence
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/compilation-settings.ts loaded",
);

import { statePersistence } from "./state-persistence.js";

export interface CompilationSettings {
  autoPreview: boolean;
  autoPreviewDelay: number; // seconds
  autoFullCompile: boolean;
  autoFullCompileDelay: number; // seconds
  compileOnSave: boolean;
  showCompilationLog: boolean;
  // Full compilation options
  addFigs?: boolean;
  addTables?: boolean;
  addDiff?: boolean;
  ppt2tif?: boolean;
  cropTif?: boolean;
  draft?: boolean;
  quiet?: boolean;
  force?: boolean;
}

const DEFAULT_SETTINGS: CompilationSettings = {
  autoPreview: true,
  autoPreviewDelay: 5,
  autoFullCompile: false,
  autoFullCompileDelay: 15,
  compileOnSave: false,
  showCompilationLog: true,
  // Full compilation options defaults
  addFigs: true,
  addTables: true,
  addDiff: false,
  ppt2tif: false,
  cropTif: false,
  draft: false,
  quiet: false,
  force: false,
};

const STORAGE_KEY = "scitex-compilation-settings";

export class CompilationSettingsManager {
  private settings: CompilationSettings;
  private settingsModal: HTMLElement | null;
  private settingsBtn: HTMLElement | null;

  constructor() {
    this.settings = this.loadSettings();
    this.settingsModal = document.getElementById("compilation-settings-modal");
    this.settingsBtn = document.getElementById("compilation-settings-btn");

    this.initialize();
    console.log("[CompilationSettings] Initialized with:", this.settings);
  }

  /**
   * Initialize settings UI and apply saved preferences
   */
  private initialize(): void {
    // Apply settings to UI
    this.applySettingsToUI();

    // Setup settings button click handler
    if (this.settingsBtn) {
      this.settingsBtn.addEventListener("click", () => {
        this.openSettings();
      });
    }

    // Setup modal form handlers
    this.setupModalHandlers();

    console.log("[CompilationSettings] UI initialized");
  }

  /**
   * Load settings from localStorage
   */
  private loadSettings(): CompilationSettings {
    try {
      // First try to load from unified state persistence
      const persistedSettings = statePersistence.getSavedCompilationSettings();
      if (persistedSettings) {
        console.log("[CompilationSettings] Loaded from state persistence:", persistedSettings);
        return { ...DEFAULT_SETTINGS, ...persistedSettings };
      }

      // Fallback to old localStorage key
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        return { ...DEFAULT_SETTINGS, ...parsed };
      }
    } catch (error) {
      console.error("[CompilationSettings] Error loading settings:", error);
    }
    return { ...DEFAULT_SETTINGS };
  }

  /**
   * Save settings to localStorage
   */
  private saveSettings(): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.settings));

      // Also save to unified state persistence
      statePersistence.saveCompilationSettings({
        autoPreview: this.settings.autoPreview,
        autoPreviewDelay: this.settings.autoPreviewDelay,
        autoFull: this.settings.autoFullCompile,
        autoFullDelay: this.settings.autoFullCompileDelay,
        compileOnSave: this.settings.compileOnSave,
        showLog: this.settings.showCompilationLog,
        addFigs: this.settings.addFigs,
        addTables: this.settings.addTables,
        addDiff: this.settings.addDiff,
        ppt2tif: this.settings.ppt2tif,
        cropTif: this.settings.cropTif,
        draft: this.settings.draft,
        quiet: this.settings.quiet,
        force: this.settings.force,
      });

      console.log("[CompilationSettings] Settings saved:", this.settings);
    } catch (error) {
      console.error("[CompilationSettings] Error saving settings:", error);
    }
  }

  /**
   * Apply settings to UI elements
   */
  private applySettingsToUI(): void {
    // Auto Preview checkbox
    const autoPreviewCheckbox = document.getElementById(
      "auto-preview-checkbox-panel",
    ) as HTMLInputElement;
    if (autoPreviewCheckbox) {
      autoPreviewCheckbox.checked = this.settings.autoPreview;
    }

    // Auto Full Compile checkbox
    const autoFullCompileCheckbox = document.getElementById(
      "auto-fullcompile-checkbox",
    ) as HTMLInputElement;
    if (autoFullCompileCheckbox) {
      autoFullCompileCheckbox.checked = this.settings.autoFullCompile;
    }

    // Update delay labels
    this.updateDelayLabels();
  }

  /**
   * Update delay labels in UI
   */
  private updateDelayLabels(): void {
    const autoPreviewLabel = document.querySelector(
      'label[for="auto-preview-checkbox-panel"]',
    );
    if (autoPreviewLabel) {
      const iconHtml = '<i class="fas fa-magic me-1"></i>';
      autoPreviewLabel.innerHTML = `${iconHtml}Auto Preview (${this.settings.autoPreviewDelay}s)`;
    }

    const autoFullLabel = document.querySelector(
      'label[for="auto-fullcompile-checkbox"]',
    );
    if (autoFullLabel) {
      const iconHtml = '<i class="fas fa-rocket me-1"></i>';
      autoFullLabel.innerHTML = `${iconHtml}Auto Full (${this.settings.autoFullCompileDelay}s)`;
    }
  }

  /**
   * Setup modal form handlers
   */
  private setupModalHandlers(): void {
    if (!this.settingsModal) return;

    // Save button
    const saveBtn = this.settingsModal.querySelector(
      "#save-compilation-settings",
    ) as HTMLButtonElement;
    if (saveBtn) {
      saveBtn.addEventListener("click", () => {
        this.saveFromModal();
      });
    }

    // Reset to defaults button
    const resetBtn = this.settingsModal.querySelector(
      "#reset-compilation-settings",
    ) as HTMLButtonElement;
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        this.resetToDefaults();
      });
    }

    // Close button
    const closeBtn = this.settingsModal.querySelector(
      ".btn-close",
    ) as HTMLButtonElement;
    if (closeBtn) {
      closeBtn.addEventListener("click", () => {
        this.closeSettings();
      });
    }
  }

  /**
   * Open settings modal
   */
  public openSettings(): void {
    if (!this.settingsModal) return;

    // Populate form with current settings
    this.populateSettingsForm();

    // Show modal (Bootstrap 5)
    const modal = new (window as any).bootstrap.Modal(this.settingsModal);
    modal.show();

    console.log("[CompilationSettings] Settings modal opened");
  }

  /**
   * Close settings modal
   */
  public closeSettings(): void {
    if (!this.settingsModal) return;

    const modal = (window as any).bootstrap.Modal.getInstance(
      this.settingsModal,
    );
    if (modal) {
      modal.hide();
    }
  }

  /**
   * Populate settings form with current values
   */
  private populateSettingsForm(): void {
    if (!this.settingsModal) return;

    // Auto Preview
    const autoPreviewInput = this.settingsModal.querySelector(
      "#setting-auto-preview",
    ) as HTMLInputElement;
    if (autoPreviewInput) {
      autoPreviewInput.checked = this.settings.autoPreview;
    }

    const autoPreviewDelayInput = this.settingsModal.querySelector(
      "#setting-auto-preview-delay",
    ) as HTMLInputElement;
    if (autoPreviewDelayInput) {
      autoPreviewDelayInput.value = this.settings.autoPreviewDelay.toString();
    }

    // Auto Full Compile
    const autoFullInput = this.settingsModal.querySelector(
      "#setting-auto-full",
    ) as HTMLInputElement;
    if (autoFullInput) {
      autoFullInput.checked = this.settings.autoFullCompile;
    }

    const autoFullDelayInput = this.settingsModal.querySelector(
      "#setting-auto-full-delay",
    ) as HTMLInputElement;
    if (autoFullDelayInput) {
      autoFullDelayInput.value =
        this.settings.autoFullCompileDelay.toString();
    }

    // Compile on Save
    const compileOnSaveInput = this.settingsModal.querySelector(
      "#setting-compile-on-save",
    ) as HTMLInputElement;
    if (compileOnSaveInput) {
      compileOnSaveInput.checked = this.settings.compileOnSave;
    }

    // Show Compilation Log
    const showLogInput = this.settingsModal.querySelector(
      "#setting-show-log",
    ) as HTMLInputElement;
    if (showLogInput) {
      showLogInput.checked = this.settings.showCompilationLog;
    }
  }

  /**
   * Save settings from modal form
   */
  private saveFromModal(): void {
    if (!this.settingsModal) return;

    // Read values from form
    const autoPreviewInput = this.settingsModal.querySelector(
      "#setting-auto-preview",
    ) as HTMLInputElement;
    const autoPreviewDelayInput = this.settingsModal.querySelector(
      "#setting-auto-preview-delay",
    ) as HTMLInputElement;
    const autoFullInput = this.settingsModal.querySelector(
      "#setting-auto-full",
    ) as HTMLInputElement;
    const autoFullDelayInput = this.settingsModal.querySelector(
      "#setting-auto-full-delay",
    ) as HTMLInputElement;
    const compileOnSaveInput = this.settingsModal.querySelector(
      "#setting-compile-on-save",
    ) as HTMLInputElement;
    const showLogInput = this.settingsModal.querySelector(
      "#setting-show-log",
    ) as HTMLInputElement;

    // Update settings
    if (autoPreviewInput) {
      this.settings.autoPreview = autoPreviewInput.checked;
    }
    if (autoPreviewDelayInput) {
      this.settings.autoPreviewDelay = parseInt(
        autoPreviewDelayInput.value,
        10,
      );
    }
    if (autoFullInput) {
      this.settings.autoFullCompile = autoFullInput.checked;
    }
    if (autoFullDelayInput) {
      this.settings.autoFullCompileDelay = parseInt(
        autoFullDelayInput.value,
        10,
      );
    }
    if (compileOnSaveInput) {
      this.settings.compileOnSave = compileOnSaveInput.checked;
    }
    if (showLogInput) {
      this.settings.showCompilationLog = showLogInput.checked;
    }

    // Save to localStorage
    this.saveSettings();

    // Apply to UI
    this.applySettingsToUI();

    // Close modal
    this.closeSettings();

    // Show toast notification
    const showToast = (window as any).showToast;
    if (showToast) {
      showToast("Compilation settings saved", "success");
    }

    console.log("[CompilationSettings] Settings updated and saved");
  }

  /**
   * Reset settings to defaults
   */
  public resetToDefaults(): void {
    this.settings = { ...DEFAULT_SETTINGS };
    this.saveSettings();
    this.applySettingsToUI();
    this.populateSettingsForm();

    const showToast = (window as any).showToast;
    if (showToast) {
      showToast("Settings reset to defaults", "info");
    }

    console.log("[CompilationSettings] Reset to defaults");
  }

  /**
   * Get current settings
   */
  public getSettings(): CompilationSettings {
    return { ...this.settings };
  }

  /**
   * Update a specific setting
   */
  public updateSetting<K extends keyof CompilationSettings>(
    key: K,
    value: CompilationSettings[K],
  ): void {
    this.settings[key] = value;
    this.saveSettings();
    this.applySettingsToUI();
  }
}

// Export singleton instance
export const compilationSettings = new CompilationSettingsManager();
