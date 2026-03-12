/**
 * AxisTicksSection - Builds HTML for pltz axis & ticks section
 */

import { PropertiesHTMLBuilder } from "../PropertiesHTMLBuilder";

export interface AxisTicksSpec {
  axes?: Array<{
    limits?: { xmin?: number; xmax?: number; ymin?: number; ymax?: number };
  }>;
}

export interface AxisTicksStyle {
  x_n_ticks?: number;
  y_n_ticks?: number;
  tick_direction?: string;
  tick_fontsize?: number;
  hide_top_spine?: boolean;
  hide_right_spine?: boolean;
}

export class AxisTicksSection {
  static build(
    pltzPath: string,
    spec: AxisTicksSpec,
    style: AxisTicksStyle,
  ): string {
    const axes = spec.axes || [];
    const ax0 = axes[0] || {};
    const limits = ax0.limits || {};

    return `<div class="scitex-section">
            <div class="scitex-section-header collapsed" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                <i class="fas fa-chevron-down"></i>
                <span>Axis & Ticks</span>
            </div>
            <div class="scitex-section-content" style="display: none;">
                <div class="pltz-subsection-label">Limits</div>
                <div class="property-row">
                    <div class="property-group half">
                        <label class="property-label">X Range</label>
                        <div class="pltz-range-inputs">
                            <input type="number" class="property-input pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="spec.axes.0.limits.xmin"
                                value="${limits.xmin !== undefined ? limits.xmin : ""}"
                                placeholder="Min" step="any">
                            <input type="number" class="property-input pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="spec.axes.0.limits.xmax"
                                value="${limits.xmax !== undefined ? limits.xmax : ""}"
                                placeholder="Max" step="any">
                        </div>
                    </div>
                    <div class="property-group half">
                        <label class="property-label">Y Range</label>
                        <div class="pltz-range-inputs">
                            <input type="number" class="property-input pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="spec.axes.0.limits.ymin"
                                value="${limits.ymin !== undefined ? limits.ymin : ""}"
                                placeholder="Min" step="any">
                            <input type="number" class="property-input pltz-editable"
                                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                                data-property="spec.axes.0.limits.ymax"
                                value="${limits.ymax !== undefined ? limits.ymax : ""}"
                                placeholder="Max" step="any">
                        </div>
                    </div>
                </div>
                <div class="pltz-subsection-label pltz-subsection-label-margin">Tick Settings</div>
                <div class="property-row">
                    <div class="property-group half">
                        <label class="property-label">X Ticks</label>
                        <input type="number" class="property-input pltz-editable"
                            data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                            data-property="style.x_n_ticks"
                            value="${style.x_n_ticks || 5}"
                            step="1" min="2" max="15">
                    </div>
                    <div class="property-group half">
                        <label class="property-label">Y Ticks</label>
                        <input type="number" class="property-input pltz-editable"
                            data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                            data-property="style.y_n_ticks"
                            value="${style.y_n_ticks || 5}"
                            step="1" min="2" max="15">
                    </div>
                </div>
                <div class="property-row">
                    <div class="property-group half">
                        <label class="property-label">Tick Direction</label>
                        <select class="property-input pltz-editable"
                            data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                            data-property="style.tick_direction">
                            <option value="out" ${style.tick_direction === "out" ? "selected" : ""}>Out</option>
                            <option value="in" ${style.tick_direction === "in" ? "selected" : ""}>In</option>
                            <option value="inout" ${style.tick_direction === "inout" ? "selected" : ""}>Both</option>
                        </select>
                    </div>
                    <div class="property-group half">
                        <label class="property-label">Tick Font (pt)</label>
                        <input type="number" class="property-input pltz-editable"
                            data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                            data-property="style.tick_fontsize"
                            value="${style.tick_fontsize || 7}"
                            step="1" min="4" max="16">
                    </div>
                </div>
                <div class="property-row pltz-spine-checkboxes">
                    <label class="checkbox-field">
                        <input type="checkbox" class="pltz-editable"
                            data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                            data-property="style.hide_top_spine"
                            ${style.hide_top_spine !== false ? "checked" : ""}>
                        <span>Hide Top</span>
                    </label>
                    <label class="checkbox-field">
                        <input type="checkbox" class="pltz-editable"
                            data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                            data-property="style.hide_right_spine"
                            ${style.hide_right_spine !== false ? "checked" : ""}>
                        <span>Hide Right</span>
                    </label>
                </div>
            </div>
        </div>`;
  }
}
