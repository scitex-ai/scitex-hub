/**
 * BundleLoader - Handles SciTeX bundle file loading
 *
 * Responsibilities:
 * - Load .pltz, .figz, .statsz zip bundles
 * - Load .pltz.d, .figz.d, .statsz.d directory bundles
 * - Display bundle preview cards (PNG, SVG, PDF, CSV)
 * - Parse and display bundle metadata
 *
 * Extracted from image-viewer.ts for single responsibility.
 */

import { setText, setStyle, showElement, hideElement, formatFileSize, escapeHtml } from './_viewer-utils';

export interface BundleFiles {
    [filename: string]: File;
}

export interface BundleState {
    files: BundleFiles;
    type: string | null;
    dimensions: { width?: number; height?: number } | null;
}

/**
 * Load a zipped bundle file (.pltz, .figz, .statsz)
 */
export function loadZipBundle(
    file: File,
    elements: {
        singleFilePreview: HTMLElement;
        bundleFiguresContainer: HTMLElement;
        uploadZone: HTMLElement;
        contentArea: HTMLElement;
    }
): void {
    elements.singleFilePreview.style.display = 'none';
    elements.bundleFiguresContainer.style.display = 'block';
    elements.uploadZone.style.display = 'none';
    elements.contentArea.style.display = 'block';

    const name = file.name.toLowerCase();
    let bundleType = 'unknown';
    let bundleTypeShort = 'bundle';
    if (name.includes('.pltz')) { bundleType = 'PLTZ (Plot Bundle)'; bundleTypeShort = 'pltz'; }
    else if (name.includes('.figz')) { bundleType = 'FIGZ (Figure Bundle)'; bundleTypeShort = 'figz'; }
    else if (name.includes('.statsz')) { bundleType = 'STATSZ (Stats Bundle)'; bundleTypeShort = 'statsz'; }

    setText('previewTitle', `📦 ${bundleType}`);
    hideElement('pdfPageCountRow');
    hideElement('dpiAlert');
    hideElement('pngCard');
    hideElement('svgCard');
    hideElement('pdfCard');
    hideElement('csvContainer');

    const grid = document.getElementById('bundleFiguresGrid') as HTMLElement;
    grid.innerHTML = `
        <div class="bundle-figure-card" style="grid-column: 1 / -1;">
            <div style="text-align: center; padding: 40px; color: var(--text-secondary);">
                <div style="font-size: 64px; margin-bottom: 16px;">📦</div>
                <h4 style="color: var(--text-primary); margin-bottom: 12px;">${file.name}</h4>
                <p>ZIP bundle uploaded. Metadata shown in the panel.</p>
                <p style="font-size: 12px; margin-top: 12px;">
                    💡 For full figure preview, extract and upload as folder:<br>
                    <code style="background: var(--bg-primary); padding: 4px 8px; border-radius: 4px;">
                        unzip ${file.name} -d ${file.name.replace(/\.(pltz|figz|statsz)$/i, '')}.${bundleTypeShort}.d
                    </code>
                </p>
            </div>
        </div>
    `;
}

/**
 * Load a directory bundle (.pltz.d, .figz.d, .statsz.d)
 */
export function loadFolderBundle(
    files: FileList,
    elements: {
        uploadZone: HTMLElement;
        contentArea: HTMLElement;
        singleFilePreview: HTMLElement;
        bundleFiguresContainer: HTMLElement;
    },
    updateDimensionsCallback: (dims: { width: number; height: number }) => void
): BundleState {
    const fileArray = Array.from(files);
    const firstPath = (files[0] as any).webkitRelativePath || files[0].name;
    const folderName = firstPath.split('/')[0];

    let bundleType = 'unknown';
    const folderLower = folderName.toLowerCase();
    if (folderLower.endsWith('.pltz.d')) bundleType = 'pltz';
    else if (folderLower.endsWith('.figz.d')) bundleType = 'figz';
    else if (folderLower.endsWith('.statsz.d')) bundleType = 'statsz';

    const bundleFiles: BundleFiles = {};
    fileArray.forEach(f => {
        const relativePath = (f as any).webkitRelativePath || f.name;
        const fileName = relativePath.split('/').pop() || '';
        bundleFiles[fileName] = f;
    });

    elements.uploadZone.style.display = 'none';
    elements.contentArea.style.display = 'block';
    elements.singleFilePreview.style.display = 'none';
    elements.bundleFiguresContainer.style.display = 'block';

    const bundleTypeLabel = bundleType.toUpperCase() + ' Directory Bundle';
    setText('previewTitle', `📦 ${bundleTypeLabel}`);
    hideElement('pdfPageCountRow');
    hideElement('dpiAlert');

    const pngFile = bundleFiles['plot.png'] || bundleFiles['figure.png'];
    const svgFile = bundleFiles['plot.svg'] || bundleFiles['figure.svg'];
    const pdfFile = bundleFiles['plot.pdf'] || bundleFiles['figure.pdf'];
    const csvFile = bundleFiles['plot.csv'];
    const specFiles: Record<string, string> = { 'pltz': 'plot.json', 'figz': 'figure.json', 'statsz': 'stats.json' };
    const jsonFile = bundleFiles[specFiles[bundleType]];

    loadBundlePng(pngFile, updateDimensionsCallback);
    loadBundleSvg(svgFile);
    loadBundlePdf(pdfFile);
    loadBundleCsv(csvFile);

    setText('fileName', folderName);
    setText('fileSize', formatFileSize(fileArray.reduce((sum, f) => sum + f.size, 0)));
    setText('fileType', `${bundleType}.d (directory bundle)`);

    showElement('bundleInfoSection');
    setText('bundleType', bundleType.toUpperCase() + '.d');
    setText('bundleHasPng', pngFile ? '✓ Yes' : '✗ No');
    setText('bundleHasSvg', svgFile ? '✓ Yes' : '✗ No');
    setText('bundleHasPdf', pdfFile ? '✓ Yes' : '✗ No');
    setText('bundleHasCsv', csvFile ? '✓ Yes' : '✗ No');

    const fileList = fileArray.map(f => {
        const name = ((f as any).webkitRelativePath || f.name).split('/').slice(1).join('/');
        return name || f.name;
    }).filter(n => n);

    if (fileList.length > 0) {
        showElement('bundlePanelsRow');
        (document.getElementById('bundlePanelsList') as HTMLElement).innerHTML = fileList.map(f => `• ${f}`).join('<br>');
    }

    showElement('metadataSection');

    if (jsonFile) {
        loadBundleJsonSpec(jsonFile);
    } else {
        setText('metadataStatus', '○ No spec file found');
        setStyle('metadataStatus', 'color', 'var(--text-secondary)');
        setText('metadataContent', '');
        hideElement('copyMetadataBtn');
    }

    return {
        files: bundleFiles,
        type: bundleType,
        dimensions: null
    };
}

/**
 * Load JSON spec file from bundle
 */
function loadBundleJsonSpec(jsonFile: File): void {
    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const spec = JSON.parse(e.target?.result as string);
            setText('metadataStatus', '✓ JSON Spec Found (Reproducible)');
            setStyle('metadataStatus', 'color', '#4a9b7e');
            setText('metadataContent', JSON.stringify(spec, null, 2));
            showElement('copyMetadataBtn');
        } catch {
            setText('metadataStatus', '✗ Invalid JSON');
            setStyle('metadataStatus', 'color', '#d32f2f');
            setText('metadataContent', e.target?.result as string);
        }
    };
    reader.readAsText(jsonFile);
}

/**
 * Load PNG preview from bundle
 */
function loadBundlePng(
    file: File | undefined,
    updateDimensionsCallback: (dims: { width: number; height: number }) => void
): void {
    if (!file) { hideElement('pngCard'); return; }
    showElement('pngCard');
    const reader = new FileReader();
    reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
            (document.getElementById('bundlePngPreview') as HTMLImageElement).src = e.target?.result as string;
            setText('pngDimensions', `${img.width} × ${img.height} px`);
            updateDimensionsCallback({ width: img.width, height: img.height });
            setText('pixelWidth', `${img.width} px`);
            setText('pixelHeight', `${img.height} px`);
            setText('aspectRatio', (img.width / img.height).toFixed(3));
        };
        img.src = e.target?.result as string;
    };
    reader.readAsDataURL(file);
}

/**
 * Load SVG preview from bundle
 */
function loadBundleSvg(file: File | undefined): void {
    if (!file) { hideElement('svgCard'); return; }
    showElement('svgCard');
    const reader = new FileReader();
    reader.onload = (e) => {
        const container = document.getElementById('bundleSvgPreview') as HTMLElement;
        container.innerHTML = e.target?.result as string;
        const svgEl = container.querySelector('svg');
        if (svgEl) {
            const viewBox = svgEl.getAttribute('viewBox');
            if (viewBox) {
                const parts = viewBox.split(/\s+/);
                if (parts.length >= 4) {
                    setText('svgDimensions', `${parseFloat(parts[2]).toFixed(1)} × ${parseFloat(parts[3]).toFixed(1)} viewBox`);
                }
            } else {
                const w = svgEl.getAttribute('width');
                const h = svgEl.getAttribute('height');
                if (w && h) setText('svgDimensions', `${w} × ${h}`);
            }
        }
    };
    reader.readAsText(file);
}

/**
 * Load PDF preview from bundle
 */
async function loadBundlePdf(file: File | undefined): Promise<void> {
    if (!file) { hideElement('pdfCard'); return; }
    showElement('pdfCard');
    const reader = new FileReader();
    reader.onload = async (e) => {
        const typedArray = new Uint8Array(e.target?.result as ArrayBuffer);
        try {
            const pdf = await (window as any).pdfjsLib.getDocument(typedArray).promise;
            const page = await pdf.getPage(1);
            const viewport = page.getViewport({ scale: 1.0 });
            const canvas = document.getElementById('bundlePdfCanvas') as HTMLCanvasElement;
            const context = canvas.getContext('2d')!;
            canvas.height = viewport.height;
            canvas.width = viewport.width;
            await page.render({ canvasContext: context, viewport: viewport }).promise;
            const widthIn = (viewport.width / 72).toFixed(2);
            const heightIn = (viewport.height / 72).toFixed(2);
            setText('pdfDimensions', `${Math.round(viewport.width)} × ${Math.round(viewport.height)} pt (${widthIn}" × ${heightIn}")`);
        } catch (err) {
            console.error('Error loading bundle PDF:', err);
            hideElement('pdfCard');
        }
    };
    reader.readAsArrayBuffer(file);
}

/**
 * Load CSV preview from bundle
 */
function loadBundleCsv(file: File | undefined): void {
    if (!file) { hideElement('csvContainer'); return; }
    showElement('csvContainer');
    const reader = new FileReader();
    reader.onload = (e) => {
        const csvText = e.target?.result as string;
        const lines = csvText.trim().split('\n');
        if (lines.length === 0) { hideElement('csvContainer'); return; }

        const parseRow = (row: string): string[] => {
            const result: string[] = [];
            let current = '';
            let inQuotes = false;
            for (const char of row) {
                if (char === '"') inQuotes = !inQuotes;
                else if (char === ',' && !inQuotes) { result.push(current.trim()); current = ''; }
                else current += char;
            }
            result.push(current.trim());
            return result;
        };

        const headers = parseRow(lines[0]);
        const thead = document.getElementById('csvTableHead') as HTMLElement;
        const tbody = document.getElementById('csvTableBody') as HTMLElement;
        thead.innerHTML = '<tr>' + headers.map(h => `<th>${escapeHtml(h)}</th>`).join('') + '</tr>';

        const maxRows = Math.min(lines.length - 1, 100);
        let bodyHtml = '';
        for (let i = 1; i <= maxRows; i++) {
            const cells = parseRow(lines[i]);
            bodyHtml += '<tr>' + cells.map(c => `<td>${escapeHtml(c)}</td>`).join('') + '</tr>';
        }
        tbody.innerHTML = bodyHtml;

        setText('csvRowCount', String(lines.length - 1));
        setText('csvColCount', String(headers.length));
    };
    reader.readAsText(file);
}
