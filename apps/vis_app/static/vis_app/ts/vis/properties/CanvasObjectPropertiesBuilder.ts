/**
 * CanvasObjectPropertiesBuilder - Builds property panel UI for canvas objects
 *
 * Extracted from PropertiesManager.ts (~480 lines) to maintain single responsibility.
 * Handles property display for Fabric.js canvas objects including metadata and embedded info.
 */

import { PropertiesHTMLBuilder } from './PropertiesHTMLBuilder';

export class CanvasObjectPropertiesBuilder {
    /**
     * Build complete canvas object properties panel HTML
     */
    public static buildCanvasObjectPropertiesHTML(obj: any): string {
        const name = obj.name || obj.type || 'Object';
        let html = '';

        // ═══════════════════════════════════════════════════════════════
        // BASIC PROPERTIES Section
        // ═══════════════════════════════════════════════════════════════
        html += this.buildBasicPropertiesSection(obj, name);

        // ═══════════════════════════════════════════════════════════════
        // AXIS METADATA Section
        // ═══════════════════════════════════════════════════════════════
        html += this.buildAxisMetadataSection(obj);

        // ═══════════════════════════════════════════════════════════════
        // EMBEDDED INFO Section (lazy-loaded)
        // ═══════════════════════════════════════════════════════════════
        html += this.buildEmbeddedInfoSection();

        return html;
    }

    /**
     * Build Basic Properties section
     */
    private static buildBasicPropertiesSection(obj: any, name: string): string {
        let content = '';

        content += `<div class="property-group">
            <label class="property-label">Name</label>
            <input type="text" class="property-input" value="${name}" readonly>
        </div>`;

        content += `<div class="property-group">
            <label class="property-label">Type</label>
            <input type="text" class="property-input" value="${obj.type || 'unknown'}" readonly>
        </div>`;

        if (obj.width && obj.height) {
            const displayWidth = Math.round(obj.width * (obj.scaleX || 1));
            const displayHeight = Math.round(obj.height * (obj.scaleY || 1));
            content += `<div class="property-row">
                <div class="property-group half">
                    <label class="property-label">Width (px)</label>
                    <input type="text" class="property-input" value="${displayWidth}" readonly>
                </div>
                <div class="property-group half">
                    <label class="property-label">Height (px)</label>
                    <input type="text" class="property-input" value="${displayHeight}" readonly>
                </div>
            </div>`;
        }

        if (obj.left !== undefined && obj.top !== undefined) {
            content += `<div class="property-row">
                <div class="property-group half">
                    <label class="property-label">X Position</label>
                    <input type="text" class="property-input" value="${Math.round(obj.left)}" readonly>
                </div>
                <div class="property-group half">
                    <label class="property-label">Y Position</label>
                    <input type="text" class="property-input" value="${Math.round(obj.top)}" readonly>
                </div>
            </div>`;
        }

        return PropertiesHTMLBuilder.buildSection('Basic Properties', content, false);
    }

    /**
     * Build Axis Metadata section
     */
    private static buildAxisMetadataSection(obj: any): string {
        let content = '';

        if (obj.axisMetadata) {
            const meta = obj.axisMetadata;

            // Calculate current scale
            const scaleX = obj.scaleX || 1;
            const scaleY = obj.scaleY || 1;

            // Handle scitex.plt.plot schema format (has size.width_px instead of figure_size_px)
            if (!meta.figure_size_px && meta.size && meta.size.width_px) {
                meta.figure_size_px = {
                    width: meta.size.width_px,
                    height: meta.size.height_px
                };
            }

            // Estimate axes_bbox_px from scitex.plt.plot schema if not available
            if (!meta.axes_bbox_px && meta.axes && meta.axes[0] && meta.size) {
                const axesInfo = meta.axes[0];
                const sizeInfo = meta.size;
                if (axesInfo.axes_width_mm && axesInfo.axes_height_mm && sizeInfo.dpi) {
                    const dpi = sizeInfo.dpi;
                    const mmToInch = 1 / 25.4;
                    const axesWidthPx = Math.round(axesInfo.axes_width_mm * mmToInch * dpi);
                    const axesHeightPx = Math.round(axesInfo.axes_height_mm * mmToInch * dpi);

                    // Estimate position (assume 10% margin from edges for typical matplotlib)
                    const marginPx = Math.round(meta.figure_size_px.width * 0.1);
                    meta.axes_bbox_px = {
                        x: marginPx,
                        y: marginPx,
                        width: axesWidthPx,
                        height: axesHeightPx
                    };
                }
            }

            // Figure Size
            if (meta.figure_size_px) {
                content += `<div class="property-row">
                    <div class="property-group half">
                        <label class="property-label">Figure Width</label>
                        <input type="text" class="property-input" value="${meta.figure_size_px.width} px" readonly>
                    </div>
                    <div class="property-group half">
                        <label class="property-label">Figure Height</label>
                        <input type="text" class="property-input" value="${meta.figure_size_px.height} px" readonly>
                    </div>
                </div>`;
            }

            // Axes BBox
            if (meta.axes_bbox_px) {
                content += `<div class="property-row">
                    <div class="property-group half">
                        <label class="property-label">Axes X, Y</label>
                        <input type="text" class="property-input" value="${meta.axes_bbox_px.x}, ${meta.axes_bbox_px.y}" readonly>
                    </div>
                    <div class="property-group half">
                        <label class="property-label">Axes W × H</label>
                        <input type="text" class="property-input" value="${meta.axes_bbox_px.width} × ${meta.axes_bbox_px.height}" readonly>
                    </div>
                </div>`;

                // Calculate scaled axes dimensions
                const scaledAxesWidth = Math.round(meta.axes_bbox_px.width * scaleX);
                const scaledAxesHeight = Math.round(meta.axes_bbox_px.height * scaleY);

                content += `<div class="property-row">
                    <div class="property-group half">
                        <label class="property-label">Scaled Axes W</label>
                        <input type="text" class="property-input" value="${scaledAxesWidth} px" readonly>
                    </div>
                    <div class="property-group half">
                        <label class="property-label">Scaled Axes H</label>
                        <input type="text" class="property-input" value="${scaledAxesHeight} px" readonly>
                    </div>
                </div>`;
            }

            // Axis Limits
            if (meta.xlim || meta.ylim) {
                content += `<div class="property-row">`;
                if (meta.xlim) {
                    content += `<div class="property-group half">
                        <label class="property-label">X Limits</label>
                        <input type="text" class="property-input" value="[${meta.xlim[0].toFixed(2)}, ${meta.xlim[1].toFixed(2)}]" readonly>
                    </div>`;
                }
                if (meta.ylim) {
                    content += `<div class="property-group half">
                        <label class="property-label">Y Limits</label>
                        <input type="text" class="property-input" value="[${meta.ylim[0].toFixed(2)}, ${meta.ylim[1].toFixed(2)}]" readonly>
                    </div>`;
                }
                content += `</div>`;
            }

            // Copy JSON button
            content += `<button class="property-button" onclick="navigator.clipboard.writeText(JSON.stringify(${JSON.stringify(meta)}, null, 2)).then(() => console.log('Metadata copied'))" style="
                margin-top: 8px;
                padding: 4px 12px;
                font-size: 11px;
                background: var(--accent-primary, #4a9b7e);
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            ">Copy JSON</button>`;
        } else {
            content += `<div class="scitex-no-traces">
                No metadata available
            </div>`;
        }

        return PropertiesHTMLBuilder.buildSection('Axis Metadata', content, false);
    }

    /**
     * Build Embedded Info section (lazy-loaded)
     */
    private static buildEmbeddedInfoSection(): string {
        const content = `<div class="scitex-section-content" style="display: none;" id="embedded-info-content">
            <div class="scitex-no-traces" style="color: var(--text-muted, #666);">
                <i class="fas fa-spinner fa-spin"></i> Click to load embedded metadata...
            </div>
        </div>`;

        return `<div class="scitex-section">
            <div class="scitex-section-header collapsed" onclick="this.classList.toggle('collapsed'); const content = this.nextElementSibling; content.style.display = this.classList.contains('collapsed') ? 'none' : 'block'; if (!this.classList.contains('collapsed')) { window.dispatchEvent(new CustomEvent('load-embedded-info')); }">
                <i class="fas fa-chevron-down"></i>
                <span>Embedded Info</span>
            </div>
            ${content}
        </div>`;
    }

    /**
     * Build embedded info content HTML from loaded data
     */
    public static buildEmbeddedInfoContentHTML(embeddedInfo: any): string {
        if (!embeddedInfo) {
            return `<div class="scitex-no-traces" style="color: var(--text-muted, #666);">
                No embedded metadata found
            </div>`;
        }

        let content = '';

        // SciTeX metadata section
        if (embeddedInfo.scitex) {
            const scitex = embeddedInfo.scitex;
            content += `<div style="margin-bottom: 12px;">
                <div style="font-weight: 600; font-size: 11px; margin-bottom: 6px; color: var(--text-primary, #fff);">
                    SciTeX Metadata
                </div>`;

            if (scitex.figure_size_mm) {
                content += `<div class="property-row">
                    <div class="property-group half">
                        <label class="property-label">Figure W (mm)</label>
                        <input type="text" class="property-input" value="${scitex.figure_size_mm.width}" readonly>
                    </div>
                    <div class="property-group half">
                        <label class="property-label">Figure H (mm)</label>
                        <input type="text" class="property-input" value="${scitex.figure_size_mm.height}" readonly>
                    </div>
                </div>`;
            }

            if (scitex.dpi) {
                content += `<div class="property-group">
                    <label class="property-label">DPI</label>
                    <input type="text" class="property-input" value="${scitex.dpi}" readonly>
                </div>`;
            }

            if (scitex.axes && scitex.axes.length > 0) {
                const axes = scitex.axes[0];
                if (axes.xlim && axes.ylim) {
                    content += `<div class="property-row">
                        <div class="property-group half">
                            <label class="property-label">X Limits</label>
                            <input type="text" class="property-input" value="[${axes.xlim[0]}, ${axes.xlim[1]}]" readonly>
                        </div>
                        <div class="property-group half">
                            <label class="property-label">Y Limits</label>
                            <input type="text" class="property-input" value="[${axes.ylim[0]}, ${axes.ylim[1]}]" readonly>
                        </div>
                    </div>`;
                }
            }

            content += `</div>`;
        }

        // Raw JSON copy button
        content += `<button class="property-button" onclick="navigator.clipboard.writeText(JSON.stringify(${JSON.stringify(embeddedInfo)}, null, 2)).then(() => console.log('Embedded info copied'))" style="
            margin-top: 8px;
            padding: 4px 12px;
            font-size: 11px;
            background: var(--accent-primary, #4a9b7e);
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        ">Copy Full JSON</button>`;

        return content;
    }
}
