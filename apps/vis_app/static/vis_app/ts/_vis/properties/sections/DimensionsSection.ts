/**
 * DimensionsSection - Builds HTML for pltz dimensions section
 */

import { PropertiesHTMLBuilder } from "../PropertiesHTMLBuilder";

export interface PltzSize {
  width_mm?: number;
  height_mm?: number;
}

export interface DimensionsSectionStyle {
  size?: PltzSize;
  dpi?: number;
}

export class DimensionsSection {
  static build(pltzPath: string, style: DimensionsSectionStyle): string {
    const sizeMm = style.size || {};
    return `<div class="scitex-section">
            <div class="scitex-section-header collapsed" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                <i class="fas fa-chevron-down"></i>
                <span>Dimensions</span>
            </div>
            <div class="scitex-section-content" style="display: none;">
                <div class="property-group pltz-unit-group">
                    <label class="property-label">Unit</label>
                    <div class="unit-toggle">
                        <button class="unit-btn active" id="unit-mm" onclick="window.pltzSetUnit?.('mm')">mm</button>
                        <button class="unit-btn" id="unit-inch" onclick="window.pltzSetUnit?.('inch')">inch</button>
                    </div>
                </div>
                <div class="property-row">
                    <div class="property-group half">
                        <label class="property-label" id="width-label">Width (mm)</label>
                        <input type="number" class="property-input pltz-editable"
                            data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                            data-property="style.size.width_mm"
                            id="pltz-width"
                            value="${sizeMm.width_mm || 80}"
                            step="1" min="10" max="300">
                    </div>
                    <div class="property-group half">
                        <label class="property-label" id="height-label">Height (mm)</label>
                        <input type="number" class="property-input pltz-editable"
                            data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                            data-property="style.size.height_mm"
                            id="pltz-height"
                            value="${sizeMm.height_mm || 60}"
                            step="1" min="10" max="300">
                    </div>
                </div>
                <div class="property-group">
                    <label class="property-label">DPI</label>
                    <input type="number" class="property-input pltz-editable"
                        data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                        data-property="style.dpi"
                        value="${style.dpi || 300}"
                        step="1" min="72" max="600">
                </div>
            </div>
        </div>`;
  }
}
