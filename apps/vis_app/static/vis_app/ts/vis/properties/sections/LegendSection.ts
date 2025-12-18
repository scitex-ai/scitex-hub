/**
 * LegendSection - Builds HTML for pltz legend section
 */

import { PropertiesHTMLBuilder } from "../PropertiesHTMLBuilder.ts";

export interface LegendStyle {
  visible?: boolean;
  location?: string;
  ncols?: number;
  frameon?: boolean;
  fontsize?: number;
}

export class LegendSection {
  static build(pltzPath: string, style: { legend?: LegendStyle }): string {
    const legend = style.legend || {};

    return `<div class="scitex-section">
      <div class="scitex-section-header collapsed" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
        <i class="fas fa-chevron-down"></i>
        <span>Legend</span>
      </div>
      <div class="scitex-section-content" style="display: none;">
        <div class="property-group pltz-checkbox-group">
          <label class="checkbox-field">
            <input type="checkbox" class="pltz-editable"
              data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
              data-property="style.legend.visible"
              ${legend.visible !== false ? "checked" : ""}>
            <span>Show Legend</span>
          </label>
        </div>
        <div class="property-row">
          <div class="property-group half">
            <label class="property-label">Position</label>
            <select class="property-input pltz-editable"
              data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
              data-property="style.legend.location">
              <option value="best" ${legend.location === "best" || !legend.location ? "selected" : ""}>Best (auto)</option>
              <option value="upper right" ${legend.location === "upper right" ? "selected" : ""}>Upper Right</option>
              <option value="upper left" ${legend.location === "upper left" ? "selected" : ""}>Upper Left</option>
              <option value="lower right" ${legend.location === "lower right" ? "selected" : ""}>Lower Right</option>
              <option value="lower left" ${legend.location === "lower left" ? "selected" : ""}>Lower Left</option>
              <option value="center right" ${legend.location === "center right" ? "selected" : ""}>Center Right</option>
              <option value="center left" ${legend.location === "center left" ? "selected" : ""}>Center Left</option>
            </select>
          </div>
          <div class="property-group half">
            <label class="property-label">Columns</label>
            <input type="number" class="property-input pltz-editable"
              data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
              data-property="style.legend.ncols"
              value="${legend.ncols || 1}"
              step="1" min="1" max="5">
          </div>
        </div>
        <div class="property-row pltz-legend-options">
          <label class="checkbox-field">
            <input type="checkbox" class="pltz-editable"
              data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
              data-property="style.legend.frameon"
              ${legend.frameon ? "checked" : ""}>
            <span>Show Frame</span>
          </label>
          <div class="property-group legend-fontsize-group">
            <label class="property-label">Font (pt)</label>
            <input type="number" class="property-input pltz-editable"
              data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
              data-property="style.legend.fontsize"
              value="${legend.fontsize || 6}"
              step="1" min="4" max="16">
          </div>
        </div>
      </div>
    </div>`;
  }
}
