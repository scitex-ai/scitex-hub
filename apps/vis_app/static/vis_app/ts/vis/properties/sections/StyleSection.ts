/**
 * StyleSection - Builds HTML for pltz style section
 */

import { PropertiesHTMLBuilder } from "../PropertiesHTMLBuilder.ts";

export interface StyleSectionData {
  grid?: boolean;
  axis_fontsize?: number;
  facecolor?: string;
  transparent?: boolean;
}

export class StyleSection {
  static build(pltzPath: string, style: StyleSectionData): string {
    return `<div class="scitex-section">
            <div class="scitex-section-header collapsed" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                <i class="fas fa-chevron-down"></i>
                <span>Style</span>
            </div>
            <div class="scitex-section-content" style="display: none;">
                <div class="property-group pltz-checkbox-group">
                    <label class="checkbox-field">
                        <input type="checkbox" class="pltz-editable"
                            data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                            data-property="style.grid"
                            ${style.grid ? "checked" : ""}>
                        <span>Show Grid</span>
                    </label>
                </div>
                <div class="property-group">
                    <label class="property-label">Label Size (pt)</label>
                    <input type="number" class="property-input pltz-editable"
                        data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                        data-property="style.axis_fontsize"
                        value="${style.axis_fontsize || 7}"
                        step="1" min="4" max="16">
                </div>
                <div class="property-group">
                    <label class="property-label">Background</label>
                    <div class="bg-toggle">
                        <button class="bg-btn bg-btn-white ${style.facecolor === "#ffffff" ? "active" : ""}" onclick="window.pltzSetBackground?.('white')">White</button>
                        <button class="bg-btn bg-btn-trans ${style.transparent !== false ? "active" : ""}" onclick="window.pltzSetBackground?.('transparent')">Trans</button>
                        <button class="bg-btn bg-btn-black ${style.facecolor === "#000000" ? "active" : ""}" onclick="window.pltzSetBackground?.('black')">Black</button>
                    </div>
                </div>
            </div>
        </div>`;
  }
}
