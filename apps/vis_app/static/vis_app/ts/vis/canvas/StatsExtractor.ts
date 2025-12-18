/**
 * StatsExtractor - Extracts data from plot elements for statistical analysis
 *
 * Handles data extraction from selected plot elements and displays stats inspector panel.
 * Extracted from ElementSelectionManager.ts for single responsibility.
 */

export interface GroupData {
    name: string;
    values: number[];
}

export interface StatsData {
    tests: Array<{
        label?: string;
        name?: string;
        p_adj?: number | null;
        p_raw?: number | null;
        stat?: number | null;
    }>;
    effects: Array<{
        label?: string;
        name?: string;
        value?: number | null;
        note?: string;
    }>;
}

export class StatsExtractor {
    /**
     * Extract group data from selected elements for statistical testing
     */
    public extractGroupsFromSelection(
        selectedElementNames: Set<string>,
        target: any,
        csvData: any
    ): GroupData[] {
        const groups: GroupData[] = [];

        if (!target || selectedElementNames.size === 0) {
            return groups;
        }

        const bboxes = target.axisMetadata?.element_bboxes;

        if (bboxes && csvData) {
            for (const elementName of selectedElementNames) {
                const bbox = bboxes[elementName];
                if (bbox) {
                    const elementData = this.extractElementData(elementName, bbox, csvData, target);
                    if (elementData && elementData.values.length > 0) {
                        groups.push(elementData);
                    }
                }
            }
        }

        return groups;
    }

    /**
     * Extract data values for a specific element within a plot
     */
    public extractElementData(
        elementName: string,
        bbox: any,
        csvData: any,
        target: any
    ): GroupData | null {
        const elementType = bbox.element_type;
        const label = bbox.label || elementName;

        // Handle boxplot elements
        if (elementType === 'boxplot' || elementName.startsWith('boxplot_')) {
            const data = this.extractBoxplotData(elementName, csvData, label);
            if (data) return data;
        }

        // Handle bar elements
        if (elementType === 'bar' || elementName.startsWith('bar_')) {
            if (bbox.values && Array.isArray(bbox.values)) {
                return { name: label, values: bbox.values };
            }
        }

        // Check if element has direct values attached
        if (bbox.values && Array.isArray(bbox.values)) {
            return { name: label, values: bbox.values };
        }

        // Try to infer from trace_idx
        if (typeof bbox.trace_idx === 'number' && csvData) {
            const data = this.extractFromTraceIndex(bbox.trace_idx, csvData, label);
            if (data) return data;
        }

        console.warn(`[StatsExtractor] Could not extract data for element: ${elementName}`);
        return null;
    }

    /**
     * Extract boxplot data from CSV
     */
    private extractBoxplotData(elementName: string, csvData: any, label: string): GroupData | null {
        const match = elementName.match(/boxplot_(\d+)/);
        if (!match) return null;

        const boxIndex = parseInt(match[1], 10);

        if (csvData && csvData.rows && csvData.columns) {
            const yColPatterns = [
                `y_${boxIndex}`,
                `value_${boxIndex}`,
                csvData.columns[boxIndex + 1],
            ];

            for (const pattern of yColPatterns) {
                if (csvData.columns.includes(pattern)) {
                    const values = csvData.rows
                        .map((row: any) => parseFloat(row[pattern]))
                        .filter((v: number) => !isNaN(v));

                    if (values.length > 0) {
                        return { name: label, values };
                    }
                }
            }

            const colName = csvData.columns[boxIndex + 1];
            if (colName) {
                const values = csvData.rows
                    .map((row: any) => parseFloat(row[colName]))
                    .filter((v: number) => !isNaN(v));

                if (values.length > 0) {
                    return { name: label, values };
                }
            }
        }

        return null;
    }

    /**
     * Extract data from trace index
     */
    private extractFromTraceIndex(traceIdx: number, csvData: any, label: string): GroupData | null {
        const colIdx = traceIdx + 1;
        const colName = csvData.columns?.[colIdx];
        if (colName) {
            const values = csvData.rows
                ?.map((row: any) => parseFloat(row[colName]))
                .filter((v: number) => !isNaN(v));

            if (values && values.length > 0) {
                return { name: label, values };
            }
        }
        return null;
    }

    /**
     * Show Stats Inspector panel with data
     */
    public showStatsInspectorPanel(data: StatsData): void {
        let panel = document.getElementById('stats-inspector-panel');

        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'stats-inspector-panel';
            panel.className = 'stats-inspector-panel';
            document.body.appendChild(panel);
        }

        panel.innerHTML = this.buildPanelHTML(data);

        const closeBtn = panel.querySelector('.close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                panel!.style.display = 'none';
            });
        }

        panel.style.display = 'block';
    }

    /**
     * Build panel HTML content
     */
    private buildPanelHTML(data: StatsData): string {
        return `
            <div class="stats-inspector-header">
                <span>Statistics Inspector</span>
                <button class="close-btn">&times;</button>
            </div>
            <div class="stats-inspector-content">
                <h4>Tests</h4>
                ${this.buildTestsTable(data.tests)}
                ${data.effects.length > 0 ? this.buildEffectsTable(data.effects) : ''}
            </div>
        `;
    }

    /**
     * Build tests table HTML
     */
    private buildTestsTable(tests: StatsData['tests']): string {
        if (tests.length === 0) return '<p>No tests run yet</p>';

        const rows = tests.map(t => `
            <tr>
                <td>${t.label || t.name}</td>
                <td>${this.formatPValue(t.p_adj ?? t.p_raw ?? null)}</td>
                <td>${t.stat?.toFixed(3) || '-'}</td>
            </tr>
        `).join('');

        return `
            <table class="stats-table">
                <thead>
                    <tr><th>Test</th><th>p-value</th><th>Stat</th></tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    }

    /**
     * Build effects table HTML
     */
    private buildEffectsTable(effects: StatsData['effects']): string {
        const rows = effects.map(e => `
            <tr>
                <td>${e.label || e.name}</td>
                <td>${e.value?.toFixed(3) || '-'}</td>
                <td>${e.note || '-'}</td>
            </tr>
        `).join('');

        return `
            <h4>Effect Sizes</h4>
            <table class="stats-table">
                <thead>
                    <tr><th>Measure</th><th>Value</th><th>Interpretation</th></tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    }

    /**
     * Format p-value with significance indicators
     */
    private formatPValue(p: number | null): string {
        if (p === null) return '-';
        if (p < 0.001) return '< 0.001 ***';
        if (p < 0.01) return `${p.toFixed(3)} **`;
        if (p < 0.05) return `${p.toFixed(3)} *`;
        return `${p.toFixed(3)} ns`;
    }
}
