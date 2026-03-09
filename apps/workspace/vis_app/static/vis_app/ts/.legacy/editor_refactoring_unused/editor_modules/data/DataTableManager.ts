/**
 * Data Table Manager
 * Manages Handsontable for plot data editing and CSV import/export
 */

declare const window: any;

export class DataTableManager {
    private dataTable: any = null;

    // Callbacks for editor integration
    private updateStatusCallback?: (message: string) => void;

    constructor(callbacks: {
        updateStatus?: (message: string) => void;
    }) {
        this.updateStatusCallback = callbacks.updateStatus;
    }

    /**
     * Initialize Handsontable for plot data editing
     */
    public initializeDataTable(): void {
        const container = document.getElementById('data-table-container');
        if (!container || this.dataTable) return;

        // Initialize with empty data
        const data = [
            ['', ''],
            ['', ''],
            ['', ''],
            ['', ''],
            ['', '']
        ];

        // Create Handsontable instance
        this.dataTable = new (window as any).Handsontable(container, {
            data: data,
            rowHeaders: true,
            colHeaders: ['X', 'Y'],
            contextMenu: true,
            manualColumnResize: true,
            manualRowResize: true,
            minSpareRows: 1,
            stretchH: 'all',
            licenseKey: 'non-commercial-and-evaluation',
            afterChange: (changes: any) => {
                if (changes) {
                    this.syncTableToJSON();
                }
            }
        });

        // Set up import CSV button
        const importBtn = document.getElementById('import-csv-btn');
        const fileInput = document.getElementById('csv-file-input') as HTMLInputElement;
        if (importBtn && fileInput) {
            importBtn.addEventListener('click', () => {
                fileInput.click();
            });

            fileInput.addEventListener('change', async (e) => {
                const file = (e.target as HTMLInputElement).files?.[0];
                if (file) {
                    const text = await file.text();
                    this.importCSV(text);
                    fileInput.value = ''; // Reset input
                }
            });
        }

        // Set up paste button
        const pasteBtn = document.getElementById('paste-data-btn');
        if (pasteBtn) {
            pasteBtn.addEventListener('click', async () => {
                try {
                    const text = await navigator.clipboard.readText();
                    this.importCSV(text);
                    this.updateStatusCallback?.('Data pasted from clipboard');
                } catch (error) {
                    this.updateStatusCallback?.('Failed to paste from clipboard. Please allow clipboard access.');
                }
            });
        }

        // Set up clear button
        const clearBtn = document.getElementById('clear-table-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.dataTable.loadData([['', ''], ['', ''], ['', ''], ['', ''], ['', '']]);
                this.updateStatusCallback?.('Table cleared');
            });
        }

        console.log('[DataTableManager] Data table initialized');
    }

    /**
     * Import CSV data into the table
     */
    public importCSV(csvText: string): void {
        if (!this.dataTable) return;

        const lines = csvText.trim().split('\n');
        const data: any[][] = [];

        for (const line of lines) {
            // Split by comma or tab
            const values = line.split(/,|\t/);
            data.push(values);
        }

        // Check if first row is header (contains non-numeric values)
        const firstRow = data[0];
        const hasHeaders = firstRow.some((val: string) => isNaN(parseFloat(val)));

        if (hasHeaders) {
            // Set column headers
            this.dataTable.updateSettings({
                colHeaders: firstRow
            });
            // Load data without headers
            this.dataTable.loadData(data.slice(1));
        } else {
            // Load all data including first row
            this.dataTable.loadData(data);
        }

        this.updateStatusCallback?.(`Imported ${data.length} rows`);
        this.syncTableToJSON();
    }

    /**
     * Sync table data to JSON specification
     */
    public syncTableToJSON(): void {
        if (!this.dataTable) return;

        const jsonSpec = document.getElementById('backend-json-spec') as HTMLTextAreaElement;
        if (!jsonSpec) return;

        try {
            const tableData = this.dataTable.getData();
            const spec = JSON.parse(jsonSpec.value);

            // Convert table data to array format
            const plotData: number[][] = [];
            for (const row of tableData) {
                // Skip empty rows
                if (row[0] === '' && row[1] === '') continue;

                const x = parseFloat(row[0]);
                const y = parseFloat(row[1]);

                if (!isNaN(x) && !isNaN(y)) {
                    plotData.push([x, y]);
                }
            }

            // Update plot data in spec
            if (spec.plot) {
                spec.plot.data = plotData;
                jsonSpec.value = JSON.stringify(spec, null, 2);
            }
        } catch (error) {
            console.error('[DataTableManager] Failed to sync table to JSON:', error);
        }
    }

    /**
     * Populate table from JSON specification data
     */
    public populateTableFromJSON(): void {
        if (!this.dataTable) return;

        const jsonSpec = document.getElementById('backend-json-spec') as HTMLTextAreaElement;
        if (!jsonSpec) return;

        try {
            const spec = JSON.parse(jsonSpec.value);

            if (spec.plot && spec.plot.data && Array.isArray(spec.plot.data)) {
                const data = spec.plot.data;
                const tableData: any[][] = [];

                // Convert plot data to table format
                for (const point of data) {
                    if (Array.isArray(point) && point.length >= 2) {
                        tableData.push([point[0].toString(), point[1].toString()]);
                    }
                }

                // Load data into table (disable afterChange temporarily to avoid circular updates)
                this.dataTable.updateSettings({ afterChange: null });
                this.dataTable.loadData(tableData);
                this.dataTable.updateSettings({
                    afterChange: (changes: any) => {
                        if (changes) {
                            this.syncTableToJSON();
                        }
                    }
                });

                console.log(`[DataTableManager] Loaded ${tableData.length} data points into table`);
            }
        } catch (error) {
            console.error('[DataTableManager] Failed to populate table from JSON:', error);
        }
    }

    /**
     * Get the data table instance
     */
    public getDataTable(): any {
        return this.dataTable;
    }
}
