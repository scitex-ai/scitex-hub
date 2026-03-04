# Data Table Component

A self-contained, Excel-like data table component with virtual scrolling, cell selection, copy/paste, and more.

## Features

- **Virtual scrolling** for large datasets (1000+ rows)
- **Cell/column/row selection** with drag support
- **Copy/paste operations** (Excel-compatible)
- **Fill handle** drag functionality
- **Column resizing** (Excel-like border dragging)
- **Keyboard navigation** (Arrow keys, Tab, Enter)
- **Cell editing** (Double-click or F2)

## Installation

### TypeScript

```typescript
import { DataTableManager } from '/static/shared/js/components/data-table/DataTableManager.ts';
import type { Dataset } from '/static/shared/js/components/data-table/types.ts';
```

### CSS

```html
<link rel="stylesheet" href="/static/shared/css/components/data-table/data-table.css">
```

## CSS Variables

The data-table component uses the following CSS variables that should be defined by the consuming app:

```css
/* Required variables - apps should define these */
--vis-bg-primary: /* Primary background color */
--vis-bg-secondary: /* Secondary background color */
--vis-bg-hover: /* Hover background color */
--workspace-border-default: /* Default border color */
--workspace-border-muted: /* Muted border color */
--text-primary: /* Primary text color */
--text-muted: /* Muted text color */
--status-success: /* Success color */
--status-success-bg: /* Success background color */
--status-error: /* Error color */
--status-error-bg: /* Error background color */
--status-warning: /* Warning color */
```

Example mapping in vis_app:

```css
:root {
    --vis-bg-primary: var(--workspace-bg-primary);
    --vis-bg-secondary: var(--workspace-bg-secondary);
    --vis-bg-hover: var(--workspace-bg-hover);
}
```

## Usage

### Basic Setup

```typescript
// Create manager instance
const dataTableManager = new DataTableManager(
    (msg) => console.log('Status:', msg),  // Status callback
    () => {},                               // Update column dropdowns callback
    () => {}                                // Update rulers area transform callback
);

// Initialize blank table
dataTableManager.initializeBlankTable();
dataTableManager.renderEditableDataTable();

// Setup column resizing
dataTableManager.setupColumnResizing();
```

### Loading Data

```typescript
// From Dataset object
const dataset: Dataset = {
    columns: ['Time (s)', 'Signal (mV)'],
    rows: [
        { 'Time (s)': 0, 'Signal (mV)': 0.5 },
        { 'Time (s)': 1, 'Signal (mV)': 0.8 },
    ]
};
dataTableManager.setCurrentData(dataset);
dataTableManager.renderEditableDataTable();

// From CSV file
const fileInput = document.getElementById('csv-input') as HTMLInputElement;
fileInput.addEventListener('change', (e) => {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (file) {
        dataTableManager.handleFileImport(file);
    }
});

// Load demo data
dataTableManager.loadDemoData();
dataTableManager.renderEditableDataTable();
```

### HTML Structure

```html
<div class="data-table-container">
    <!-- Table will be rendered here -->
</div>
```

## Architecture

The component is split into 7 focused modules:

- **TableData**: Data management, CSV import, demo data
- **TableRendering**: Rendering & virtual scrolling
- **TableSelection**: Cell/column/row selection
- **TableEditing**: Cell editing & keyboard navigation
- **TableClipboard**: Copy/paste operations
- **TableFillHandle**: Fill handle drag functionality
- **TableColumnRow**: Column/row operations & resizing

## API

### DataTableManager

#### Data Operations

- `getCurrentData(): Dataset | null` - Get current dataset
- `setCurrentData(data: Dataset | null): void` - Set current dataset
- `initializeBlankTable(): void` - Initialize blank table
- `handleFileImport(file: File): void` - Import CSV file
- `loadDemoData(): void` - Load demo data

#### Rendering

- `renderDataTable(): void` - Render non-editable table
- `renderEditableDataTable(): void` - Render editable table
- `generateTableHTML(data: Dataset, tableType: string): string` - Generate HTML

#### Column/Row Operations

- `setupColumnResizing(): void` - Setup column resizing
- `addColumns(count: number): void` - Add columns
- `addRows(count: number): void` - Add rows

#### Selection

- `clearSelection(): void` - Clear cell selection

## Types

```typescript
interface Dataset {
    columns: string[];
    rows: DataRow[];
}

interface DataRow {
    [key: string]: string | number;
}

interface CellPosition {
    row: number;
    col: number;
}

const TABLE_CONSTANTS = {
    ROW_HEIGHT: 33,
    COL_WIDTH: 80,
    MAX_ROWS: 32767,
    MAX_COLS: 32767,
    DEFAULT_ROWS: 1000,
    DEFAULT_COLS: 32,
};
```

## Notes

- The module uses `.ts` extensions in imports for proper ES module support
- Virtual scrolling is enabled by default for performance with large datasets
- The component is self-contained and doesn't depend on vis_app-specific code
- CSS variables allow apps to customize colors while maintaining the structure
