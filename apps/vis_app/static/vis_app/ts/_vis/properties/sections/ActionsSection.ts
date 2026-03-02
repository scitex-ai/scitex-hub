/**
 * ActionsSection - Builds HTML for pltz actions section (statistics, annotations, buttons)
 */

export class ActionsSection {
  /**
   * Build statistics section HTML
   */
  static buildStatisticsSection(): string {
    return `<div class="scitex-section">
      <div class="scitex-section-header" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
        <i class="fas fa-chevron-down"></i>
        <span>Statistics</span>
      </div>
      <div class="scitex-section-content">
        <div id="pltz-stats-container" class="pltz-stats-container">
          <div class="stats-loading">
            <i class="fas fa-spinner fa-spin"></i> Loading statistics...
          </div>
        </div>
        <button class="btn btn-secondary btn-sm pltz-refresh-stats-btn" id="pltz-refresh-stats-btn">
          <i class="fas fa-chart-bar"></i> Refresh Stats
        </button>
      </div>
    </div>`;
  }

  /**
   * Build annotations section HTML
   */
  static buildAnnotationsSection(): string {
    return `<div class="scitex-section">
      <div class="scitex-section-header scitex-section-toggle collapsed" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.classList.toggle('collapsed');">
        <i class="fas fa-chevron-right"></i>
        <span>Annotations</span>
      </div>
      <div class="scitex-section-content collapsed">
        <div class="property-group pltz-annot-text-group">
          <label class="property-label">Text</label>
          <input type="text" class="property-input" id="pltz-annot-text" placeholder="Annotation text">
        </div>
        <div class="property-row">
          <div class="property-group pltz-annot-coord-group">
            <label class="property-label">X (0-1)</label>
            <input type="number" class="property-input pltz-annot-input" id="pltz-annot-x" value="0.5" min="0" max="1" step="0.05">
          </div>
          <div class="property-group pltz-annot-coord-group">
            <label class="property-label">Y (0-1)</label>
            <input type="number" class="property-input pltz-annot-input" id="pltz-annot-y" value="0.5" min="0" max="1" step="0.05">
          </div>
          <div class="property-group pltz-annot-coord-group">
            <label class="property-label">Size</label>
            <input type="number" class="property-input pltz-annot-input" id="pltz-annot-size" value="10" min="4" max="24" step="1">
          </div>
        </div>
        <div class="property-row pltz-annot-style-row">
          <div class="property-group pltz-annot-color-group">
            <label class="property-label">Color</label>
            <input type="color" class="property-color" id="pltz-annot-color" value="#000000">
          </div>
          <div class="property-group pltz-annot-weight-group">
            <label class="property-label">Weight</label>
            <select class="property-input pltz-annot-select" id="pltz-annot-weight">
              <option value="normal">Normal</option>
              <option value="bold">Bold</option>
            </select>
          </div>
        </div>
        <button class="btn btn-secondary btn-sm pltz-add-annot-btn" id="pltz-add-annotation-btn">
          <i class="fas fa-plus"></i> Add Annotation
        </button>
        <div id="pltz-annotations-list" class="pltz-annotations-list"></div>
      </div>
    </div>`;
  }

  /**
   * Build actions buttons section HTML
   */
  static buildButtonsSection(): string {
    return `<div class="scitex-section">
      <div class="scitex-section-header">Actions</div>
      <div class="scitex-section-content pltz-actions-content">
        <div id="pltz-status" class="pltz-status"></div>
        <div class="property-row pltz-auto-update-row">
          <div class="property-group pltz-auto-update-group">
            <label class="property-label">Auto-Update</label>
            <select class="property-input pltz-auto-update-select" id="pltz-auto-update-interval">
              <option value="0">Off</option>
              <option value="500">Hot (0.5s)</option>
              <option value="1000">Fast (1s)</option>
              <option value="2000" selected>Normal (2s)</option>
              <option value="5000">Slow (5s)</option>
            </select>
          </div>
          <button class="btn btn-cta btn-sm pltz-update-now-btn" id="pltz-update-now-btn">
            Update Now
          </button>
        </div>
        <button class="btn btn-primary btn-sm pltz-action-btn" id="pltz-save-btn">
          <i class="fas fa-save"></i> Save
        </button>
        <button class="btn btn-secondary btn-sm pltz-action-btn" id="pltz-reset-btn">
          <i class="fas fa-undo"></i> Reset
        </button>
      </div>
    </div>`;
  }
}
