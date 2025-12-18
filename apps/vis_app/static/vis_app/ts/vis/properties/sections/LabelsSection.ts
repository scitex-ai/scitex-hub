/**
 * LabelsSection - Builds HTML for pltz labels section
 */

import { PropertiesHTMLBuilder } from "../PropertiesHTMLBuilder.ts";

export interface LabelsSectionSpec {
  axes?: Array<{
    labels?: { title?: string; xlabel?: string; ylabel?: string };
  }>;
  caption?: string;
}

export class LabelsSection {
  static build(pltzPath: string, spec: LabelsSectionSpec): string {
    const axes = spec.axes || [];
    const ax0 = axes[0] || {};
    const labels = ax0.labels || {};

    return `<div class="scitex-section">
            <div class="scitex-section-header" onclick="this.classList.toggle('collapsed'); this.nextElementSibling.style.display = this.classList.contains('collapsed') ? 'none' : 'block';">
                <i class="fas fa-chevron-down"></i>
                <span>Title, Labels & Caption</span>
            </div>
            <div class="scitex-section-content">
                <div class="property-group">
                    <label class="property-label">Title</label>
                    <input type="text" class="property-input pltz-editable"
                        data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                        data-property="spec.axes.0.labels.title"
                        value="${PropertiesHTMLBuilder.escapeHtml(labels.title || "")}"
                        placeholder="Plot title">
                </div>
                <div class="property-row">
                    <div class="property-group half">
                        <label class="property-label">X Label</label>
                        <input type="text" class="property-input pltz-editable"
                            data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                            data-property="spec.axes.0.labels.xlabel"
                            value="${PropertiesHTMLBuilder.escapeHtml(labels.xlabel || "")}"
                            placeholder="X axis">
                    </div>
                    <div class="property-group half">
                        <label class="property-label">Y Label</label>
                        <input type="text" class="property-input pltz-editable"
                            data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                            data-property="spec.axes.0.labels.ylabel"
                            value="${PropertiesHTMLBuilder.escapeHtml(labels.ylabel || "")}"
                            placeholder="Y axis">
                    </div>
                </div>
                <div class="property-group">
                    <label class="property-label">Caption</label>
                    <textarea class="property-input pltz-editable pltz-caption-textarea"
                        data-pltz-path="${PropertiesHTMLBuilder.escapeHtml(pltzPath)}"
                        data-property="spec.caption"
                        rows="2"
                        placeholder="Figure caption...">${PropertiesHTMLBuilder.escapeHtml(spec.caption || "")}</textarea>
                </div>
            </div>
        </div>`;
  }
}
