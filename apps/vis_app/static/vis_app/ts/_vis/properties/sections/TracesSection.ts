/**
 * TracesSection - Builds HTML for pltz traces section
 */

import { PropertiesHTMLBuilder } from "../PropertiesHTMLBuilder";

export interface TraceSpec {
  id?: string;
  label?: string;
}

export interface TraceStyle {
  trace_id?: string;
  color?: string;
  linewidth?: number;
  linestyle?: string;
  marker?: string;
  alpha?: number;
}

export interface TracesSectionData {
  traces?: TraceSpec[];
  traceStyles?: TraceStyle[];
}

export class TracesSection {
  static build(
    pltzPath: string,
    spec: { traces?: TraceSpec[] },
    style: { traces?: TraceStyle[] },
  ): string {
    const traces = spec.traces || [];
    const traceStyles = style.traces || [];

    let tracesContent = "";
    if (traces.length > 0) {
      traces.forEach((trace: TraceSpec, index: number) => {
        const traceStyle =
          traceStyles.find((ts: TraceStyle) => ts.trace_id === trace.id) || {};
        const traceLabel = trace.label || trace.id || `Trace ${index + 1}`;
        const traceColor = traceStyle.color || "#0080bf";

        tracesContent += `<div class="trace-item" style="border-left-color: ${traceColor};">
          <div class="trace-label">${PropertiesHTMLBuilder.escapeHtml(traceLabel)}</div>
          <div class="property-row">
            <div class="property-group trace-color-group">
              <label class="property-label">Color</label>
              <input type="color" class="property-input pltz-editable"
                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                data-property="style.traces.${index}.color"
                data-trace-id="${trace.id}"
                value="${traceColor}">
            </div>
            <div class="property-group trace-width-group">
              <label class="property-label">Width</label>
              <input type="number" class="property-input pltz-editable"
                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                data-property="style.traces.${index}.linewidth"
                data-trace-id="${trace.id}"
                value="${traceStyle.linewidth || 1.5}"
                step="0.5" min="0.5" max="10">
            </div>
            <div class="property-group trace-style-group">
              <label class="property-label">Style</label>
              <select class="property-input pltz-editable"
                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                data-property="style.traces.${index}.linestyle"
                data-trace-id="${trace.id}">
                <option value="-" ${traceStyle.linestyle === "-" || !traceStyle.linestyle ? "selected" : ""}>Solid</option>
                <option value="--" ${traceStyle.linestyle === "--" ? "selected" : ""}>Dashed</option>
                <option value="-." ${traceStyle.linestyle === "-." ? "selected" : ""}>Dash-dot</option>
                <option value=":" ${traceStyle.linestyle === ":" ? "selected" : ""}>Dotted</option>
              </select>
            </div>
          </div>
          <div class="property-row trace-row-2">
            <div class="property-group trace-marker-group">
              <label class="property-label">Marker</label>
              <select class="property-input pltz-editable"
                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                data-property="style.traces.${index}.marker"
                data-trace-id="${trace.id}">
                <option value="" ${!traceStyle.marker ? "selected" : ""}>None</option>
                <option value="o" ${traceStyle.marker === "o" ? "selected" : ""}>Circle</option>
                <option value="s" ${traceStyle.marker === "s" ? "selected" : ""}>Square</option>
                <option value="^" ${traceStyle.marker === "^" ? "selected" : ""}>Triangle</option>
                <option value="D" ${traceStyle.marker === "D" ? "selected" : ""}>Diamond</option>
              </select>
            </div>
            <div class="property-group trace-alpha-group">
              <label class="property-label">Alpha</label>
              <input type="range" class="property-input pltz-editable pltz-alpha-slider"
                data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                data-property="style.traces.${index}.alpha"
                data-trace-id="${trace.id}"
                value="${traceStyle.alpha || 1}"
                min="0" max="1" step="0.1">
            </div>
          </div>
        </div>`;
      });
    } else {
      tracesContent = `<div class="pltz-no-traces">
        Click on a trace in the preview to edit its properties.
      </div>`;
    }

    return `<div class="scitex-section">
      <div class="scitex-section-header" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
        <i class="fas fa-chevron-down"></i>
        <span>Traces${traces.length > 0 ? ` (${traces.length})` : ""}</span>
      </div>
      <div class="scitex-section-content">${tracesContent}</div>
    </div>`;
  }
}
