/**
 * Export Functionality Module
 *
 * Handles:
 * - PNG export
 * - PDF export
 * - SVG export
 * - Data export
 */

export interface ExportOptions {
    format: 'png' | 'pdf' | 'svg' | 'csv';
    filename?: string;
    width?: number;
    height?: number;
    quality?: number;
}

export interface ExportFunctionality {
    exportAsPNG(options?: Partial<ExportOptions>): Promise<void>;
    exportAsPDF(options?: Partial<ExportOptions>): Promise<void>;
    exportAsSVG(options?: Partial<ExportOptions>): Promise<void>;
    exportAsCSV(data: any[], options?: Partial<ExportOptions>): Promise<void>;
}

/**
 * Setup export functionality
 */
export function setupExportFunctionality(): ExportFunctionality {
    /**
     * Export plot as PNG
     */
    async function exportAsPNG(options: Partial<ExportOptions> = {}): Promise<void> {
        const filename = options.filename || `plot-${Date.now()}.png`;
        const width = options.width || 1200;
        const height = options.height || 800;

        console.log(`[ExportFunctionality] Exporting as PNG: ${filename} (${width}x${height})`);

        const plotContainer = document.getElementById('plot-container');
        if (!plotContainer) {
            console.error('[ExportFunctionality] Plot container not found');
            return;
        }

        try {
            // Use Plotly's built-in export if available
            if (typeof (window as any).Plotly !== 'undefined') {
                await (window as any).Plotly.downloadImage(plotContainer, {
                    format: 'png',
                    width: width,
                    height: height,
                    filename: filename.replace('.png', '')
                });
                console.log('[ExportFunctionality] PNG export successful');
            } else {
                console.error('[ExportFunctionality] Plotly.js not available');
            }
        } catch (error) {
            console.error('[ExportFunctionality] PNG export failed:', error);
        }
    }

    /**
     * Export plot as PDF
     */
    async function exportAsPDF(options: Partial<ExportOptions> = {}): Promise<void> {
        const filename = options.filename || `plot-${Date.now()}.pdf`;
        const width = options.width || 1200;
        const height = options.height || 800;

        console.log(`[ExportFunctionality] Exporting as PDF: ${filename} (${width}x${height})`);

        const plotContainer = document.getElementById('plot-container');
        if (!plotContainer) {
            console.error('[ExportFunctionality] Plot container not found');
            return;
        }

        try {
            if (typeof (window as any).Plotly !== 'undefined') {
                // First export as PNG, then convert to PDF
                const imgData = await (window as any).Plotly.toImage(plotContainer, {
                    format: 'png',
                    width: width,
                    height: height
                });

                // Create download link
                const link = document.createElement('a');
                link.download = filename;
                link.href = imgData;
                link.click();

                console.log('[ExportFunctionality] PDF export successful');
            } else {
                console.error('[ExportFunctionality] Plotly.js not available');
            }
        } catch (error) {
            console.error('[ExportFunctionality] PDF export failed:', error);
        }
    }

    /**
     * Export plot as SVG
     */
    async function exportAsSVG(options: Partial<ExportOptions> = {}): Promise<void> {
        const filename = options.filename || `plot-${Date.now()}.svg`;
        const width = options.width || 1200;
        const height = options.height || 800;

        console.log(`[ExportFunctionality] Exporting as SVG: ${filename} (${width}x${height})`);

        const plotContainer = document.getElementById('plot-container');
        if (!plotContainer) {
            console.error('[ExportFunctionality] Plot container not found');
            return;
        }

        try {
            if (typeof (window as any).Plotly !== 'undefined') {
                await (window as any).Plotly.downloadImage(plotContainer, {
                    format: 'svg',
                    width: width,
                    height: height,
                    filename: filename.replace('.svg', '')
                });
                console.log('[ExportFunctionality] SVG export successful');
            } else {
                console.error('[ExportFunctionality] Plotly.js not available');
            }
        } catch (error) {
            console.error('[ExportFunctionality] SVG export failed:', error);
        }
    }

    /**
     * Export data as CSV
     */
    async function exportAsCSV(data: any[], options: Partial<ExportOptions> = {}): Promise<void> {
        const filename = options.filename || `data-${Date.now()}.csv`;

        console.log(`[ExportFunctionality] Exporting as CSV: ${filename}`);

        if (!data || data.length === 0) {
            console.error('[ExportFunctionality] No data to export');
            return;
        }

        try {
            // Convert data to CSV
            const headers = Object.keys(data[0]);
            const csvRows = [headers.join(',')];

            data.forEach(row => {
                const values = headers.map(header => {
                    const value = row[header];
                    // Escape values containing commas or quotes
                    if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                        return `"${value.replace(/"/g, '""')}"`;
                    }
                    return value;
                });
                csvRows.push(values.join(','));
            });

            const csvContent = csvRows.join('\n');

            // Create download link
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = filename;
            link.click();

            console.log('[ExportFunctionality] CSV export successful');
        } catch (error) {
            console.error('[ExportFunctionality] CSV export failed:', error);
        }
    }

    return {
        exportAsPNG,
        exportAsPDF,
        exportAsSVG,
        exportAsCSV
    };
}
