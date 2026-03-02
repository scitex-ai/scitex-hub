/**
 * State Persistence Manager
 * Saves and restores editor state across page refreshes
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/state-persistence.ts loaded",
);

interface EditorState {
  doctype?: string;
  sectionId?: string;
  // Per-doctype section memory
  sectionPerDoctype?: {
    manuscript?: string;
    supplementary?: string;
    revision?: string;
    shared?: string;
  };
  cursorPosition?: {
    lineNumber: number;
    column: number;
  };
  scrollPosition?: {
    scrollTop: number;
    scrollLeft: number;
  };
  pdfScrollPosition?: {
    scrollTop: number;
    scrollLeft: number;
  };
  activePane?: string; // 'pdf' or 'citations'
  compilationSettings?: {
    autoPreview?: boolean;
    autoPreviewDelay?: number;
    autoFull?: boolean;
    autoFullDelay?: number;
    compileOnSave?: boolean;
    showLog?: boolean;
    addFigs?: boolean;
    addTables?: boolean;
    addDiff?: boolean;
    ppt2tif?: boolean;
    cropTif?: boolean;
    draft?: boolean;
    quiet?: boolean;
    force?: boolean;
  };
  citationsSorting?: string; // sort key like 'author', 'year', 'title'
  figuresSorting?: string; // sort key like 'name', 'size', 'recent'
  tablesSorting?: string; // sort key like 'name', 'size', 'recent'
  selectedFigures?: string[]; // Array of selected figure keys (file_name or label)
  pdfZoom?: number; // PDF zoom level percentage (50-300)
  panelWidth?: number; // Left panel width percentage (20-80)
}

export class StatePersistenceManager {
  private readonly STORAGE_KEY = "scitex_writer_state";

  /**
   * Save current editor state to localStorage
   */
  public saveState(state: EditorState): void {
    try {
      const existingState = this.loadState();
      const mergedState = { ...existingState, ...state };
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(mergedState));
      console.log("[StatePersistence] State saved:", state);
    } catch (error) {
      console.error("[StatePersistence] Failed to save state:", error);
    }
  }

  /**
   * Load editor state from localStorage
   */
  public loadState(): EditorState {
    try {
      const stateJson = localStorage.getItem(this.STORAGE_KEY);
      if (stateJson) {
        const state = JSON.parse(stateJson) as EditorState;
        console.log("[StatePersistence] State loaded:", state);
        return state;
      }
    } catch (error) {
      console.error("[StatePersistence] Failed to load state:", error);
    }
    return {};
  }

  /**
   * Clear saved state
   */
  public clearState(): void {
    try {
      localStorage.removeItem(this.STORAGE_KEY);
      console.log("[StatePersistence] State cleared");
    } catch (error) {
      console.error("[StatePersistence] Failed to clear state:", error);
    }
  }

  /**
   * Save doctype selection
   */
  public saveDoctype(doctype: string): void {
    this.saveState({ doctype });
  }

  /**
   * Save section selection
   */
  public saveSection(sectionId: string): void {
    this.saveState({ sectionId });
  }

  /**
   * Save section for a specific doctype
   */
  public saveSectionForDoctype(doctype: string, sectionId: string): void {
    const state = this.loadState();
    const sectionPerDoctype = state.sectionPerDoctype || {};
    sectionPerDoctype[doctype as keyof typeof sectionPerDoctype] = sectionId;
    this.saveState({ sectionPerDoctype, sectionId }); // Also update current sectionId
    console.log(`[StatePersistence] Saved section for ${doctype}:`, sectionId);
  }

  /**
   * Get saved section for a specific doctype
   */
  public getSavedSectionForDoctype(doctype: string): string | undefined {
    const state = this.loadState();
    const section = state.sectionPerDoctype?.[doctype as keyof typeof state.sectionPerDoctype];
    console.log(`[StatePersistence] Retrieved section for ${doctype}:`, section);
    return section;
  }

  /**
   * Save cursor position
   */
  public saveCursorPosition(lineNumber: number, column: number): void {
    this.saveState({ cursorPosition: { lineNumber, column } });
  }

  /**
   * Save scroll position
   */
  public saveScrollPosition(scrollTop: number, scrollLeft: number): void {
    this.saveState({ scrollPosition: { scrollTop, scrollLeft } });
  }

  /**
   * Get saved doctype
   */
  public getSavedDoctype(): string | undefined {
    return this.loadState().doctype;
  }

  /**
   * Get saved section
   */
  public getSavedSection(): string | undefined {
    return this.loadState().sectionId;
  }

  /**
   * Get saved cursor position
   */
  public getSavedCursorPosition(): { lineNumber: number; column: number } | undefined {
    return this.loadState().cursorPosition;
  }

  /**
   * Get saved scroll position
   */
  public getSavedScrollPosition(): { scrollTop: number; scrollLeft: number } | undefined {
    return this.loadState().scrollPosition;
  }

  /**
   * Save PDF scroll position
   */
  public savePdfScrollPosition(scrollTop: number, scrollLeft: number): void {
    this.saveState({ pdfScrollPosition: { scrollTop, scrollLeft } });
  }

  /**
   * Get saved PDF scroll position
   */
  public getSavedPdfScrollPosition(): { scrollTop: number; scrollLeft: number } | undefined {
    return this.loadState().pdfScrollPosition;
  }

  /**
   * Save active pane (pdf or citations)
   */
  public saveActivePane(pane: string): void {
    this.saveState({ activePane: pane });
    console.log("[StatePersistence] Saved active pane:", pane);
  }

  /**
   * Get saved active pane
   */
  public getSavedActivePane(): string | undefined {
    const pane = this.loadState().activePane;
    console.log("[StatePersistence] Retrieved active pane:", pane);
    return pane;
  }

  /**
   * Save compilation settings
   */
  public saveCompilationSettings(settings: {
    autoPreview?: boolean;
    autoPreviewDelay?: number;
    autoFull?: boolean;
    autoFullDelay?: number;
    compileOnSave?: boolean;
    showLog?: boolean;
    addFigs?: boolean;
    addTables?: boolean;
    addDiff?: boolean;
    ppt2tif?: boolean;
    cropTif?: boolean;
    draft?: boolean;
    quiet?: boolean;
    force?: boolean;
  }): void {
    this.saveState({ compilationSettings: settings });
  }

  /**
   * Get saved compilation settings
   */
  public getSavedCompilationSettings(): {
    autoPreview?: boolean;
    autoPreviewDelay?: number;
    autoFull?: boolean;
    autoFullDelay?: number;
    compileOnSave?: boolean;
    showLog?: boolean;
    addFigs?: boolean;
    addTables?: boolean;
    addDiff?: boolean;
    ppt2tif?: boolean;
    cropTif?: boolean;
    draft?: boolean;
    quiet?: boolean;
    force?: boolean;
  } | undefined {
    return this.loadState().compilationSettings;
  }

  /**
   * Save citations sorting
   */
  public saveCitationsSorting(sorting: string): void {
    this.saveState({ citationsSorting: sorting });
  }

  /**
   * Get saved citations sorting
   */
  public getSavedCitationsSorting(): string | undefined {
    return this.loadState().citationsSorting;
  }

  /**
   * Save figures sorting
   */
  public saveFiguresSorting(sorting: string): void {
    this.saveState({ figuresSorting: sorting });
  }

  /**
   * Get saved figures sorting
   */
  public getSavedFiguresSorting(): string | undefined {
    return this.loadState().figuresSorting;
  }

  /**
   * Save tables sorting
   */
  public saveTablesSorting(sorting: string): void {
    this.saveState({ tablesSorting: sorting });
  }

  /**
   * Get saved tables sorting
   */
  public getSavedTablesSorting(): string | undefined {
    return this.loadState().tablesSorting;
  }

  /**
   * Save PDF zoom level
   */
  public savePdfZoom(zoom: number): void {
    this.saveState({ pdfZoom: zoom });
    console.log("[StatePersistence] Saved PDF zoom:", zoom);
  }

  /**
   * Get saved PDF zoom level
   */
  public getSavedPdfZoom(): number | undefined {
    const zoom = this.loadState().pdfZoom;
    console.log("[StatePersistence] Retrieved PDF zoom:", zoom);
    return zoom;
  }

  /**
   * Save panel width (left panel percentage)
   */
  public savePanelWidth(widthPercent: number): void {
    this.saveState({ panelWidth: widthPercent });
    console.log("[StatePersistence] Saved panel width:", widthPercent);
  }

  /**
   * Get saved panel width
   */
  public getSavedPanelWidth(): number | undefined {
    const width = this.loadState().panelWidth;
    console.log("[StatePersistence] Retrieved panel width:", width);
    return width;
  }
}

// Export singleton instance
export const statePersistence = new StatePersistenceManager();
