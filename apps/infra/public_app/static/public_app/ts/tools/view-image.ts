/**
 * Image Viewer Tool - Figure dimension and metadata inspector
 * Supports: PNG, JPG, SVG, PDF, SciTeX bundles (.pltz, .figz)
 *
 * Refactored: BundleLoader handles bundle file loading.
 */

import { loadZipBundle, loadFolderBundle as loadFolderBundleImpl, BundleState } from './_BundleLoader';
import { setText, setStyle, showElement, hideElement, formatFileSize } from './_viewer-utils';

// State variables
let currentImage: HTMLImageElement | null = null;
let currentFile: File | null = null;
let currentDpi = 300;
let currentPdf: any = null;
let currentPdfPage = 1;
let totalPdfPages = 0;
let isPdfFile = false;
let isSvgFile = false;
let isBundle = false;
let currentDimensions: { width?: number; height?: number; width_pt?: number; height_pt?: number; unit?: string } | null = null;
let currentBundleFiles: Record<string, File> = {};
let currentBundleType: string | null = null;

// DOM Elements
const uploadZone = document.getElementById('uploadZone') as HTMLElement;
const fileInput = document.getElementById('fileInput') as HTMLInputElement;
const folderInput = document.getElementById('folderInput') as HTMLInputElement;
const contentArea = document.getElementById('contentArea') as HTMLElement;
const imagePreview = document.getElementById('imagePreview') as HTMLImageElement;
const svgPreview = document.getElementById('svgPreview') as HTMLElement;
const pdfCanvas = document.getElementById('pdfCanvas') as HTMLCanvasElement;
const pdfControls = document.getElementById('pdfControls') as HTMLElement;
const singleFilePreview = document.getElementById('singleFilePreview') as HTMLElement;
const bundleFiguresContainer = document.getElementById('bundleFiguresContainer') as HTMLElement;

// Initialize event listeners
export function initImageViewer(): void {
  setupUploadHandlers();
  setupControlHandlers();
  setupPdfNavigation();
}

function setupUploadHandlers(): void {
  document.getElementById('uploadFileBtn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  document.getElementById('uploadFolderBtn')?.addEventListener('click', (e) => {
    e.stopPropagation();
    folderInput.click();
  });

  folderInput.addEventListener('change', (e) => {
    const files = (e.target as HTMLInputElement).files;
    if (files && files.length > 0) {
      loadFolderBundle(files);
    }
  });

  uploadZone.addEventListener('click', (e) => {
    if ((e.target as HTMLElement).id !== 'uploadFileBtn' && (e.target as HTMLElement).id !== 'uploadFolderBtn') {
      fileInput.click();
    }
  });

  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.style.borderColor = '#3a7c65';
  });

  uploadZone.addEventListener('dragleave', () => {
    uploadZone.style.borderColor = '#4a9b7e';
  });

  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.style.borderColor = '#4a9b7e';
    const file = e.dataTransfer?.files[0];
    if (file && isValidFileType(file)) {
      loadFile(file);
    }
  });

  fileInput.addEventListener('change', (e) => {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (file) loadFile(file);
  });
}

function isValidFileType(file: File): boolean {
  const name = file.name.toLowerCase();
  return file.type.startsWith('image/') ||
         file.type === 'application/pdf' ||
         file.type === 'application/zip' ||
         name.endsWith('.svg') ||
         name.endsWith('.pltz') || name.endsWith('.pltz.d') ||
         name.endsWith('.figz') || name.endsWith('.figz.d') ||
         name.endsWith('.statsz') || name.endsWith('.statsz.d');
}

function setupControlHandlers(): void {
  document.getElementById('clearBtn')?.addEventListener('click', clearViewer);

  document.getElementById('applyDpiBtn')?.addEventListener('click', () => {
    const input = document.getElementById('customDpi') as HTMLInputElement;
    const customDpiValue = parseInt(input.value);
    if (customDpiValue > 0 && customDpiValue <= 10000) {
      currentDpi = customDpiValue;
      updatePhysicalSize();
    } else {
      alert('Please enter a valid DPI value (1-10000)');
    }
  });

  document.getElementById('copyMetadataBtn')?.addEventListener('click', copyMetadata);
}

function setupPdfNavigation(): void {
  document.getElementById('prevPage')?.addEventListener('click', () => {
    if (currentPdfPage > 1) {
      currentPdfPage--;
      renderPdfPage(currentPdfPage);
    }
  });

  document.getElementById('nextPage')?.addEventListener('click', () => {
    if (currentPdfPage < totalPdfPages) {
      currentPdfPage++;
      renderPdfPage(currentPdfPage);
    }
  });
}

function clearViewer(): void {
  contentArea.style.display = 'none';
  uploadZone.style.display = 'block';
  currentImage = null;
  currentFile = null;
  currentPdf = null;
  isPdfFile = false;
  isSvgFile = false;
  isBundle = false;
  currentBundleFiles = {};
  currentBundleType = null;
  fileInput.value = '';
  folderInput.value = '';

  imagePreview.style.display = 'none';
  svgPreview.style.display = 'none';
  svgPreview.innerHTML = '';
  pdfCanvas.style.display = 'none';
  pdfControls.style.display = 'none';
  singleFilePreview.style.display = 'block';

  bundleFiguresContainer.style.display = 'none';
  hideElement('pngCard');
  hideElement('svgCard');
  hideElement('pdfCard');
  hideElement('csvContainer');
  (document.getElementById('bundlePngPreview') as HTMLImageElement).src = '';
  (document.getElementById('bundleSvgPreview') as HTMLElement).innerHTML = '';

  hideElement('metadataSection');
  (document.getElementById('metadataContent') as HTMLElement).textContent = '';
  hideElement('copyMetadataBtn');
  hideElement('pdfPageCountRow');
  hideElement('bundleInfoSection');
}

async function copyMetadata(): Promise<void> {
  const metadataContent = document.getElementById('metadataContent')?.textContent || '';
  const copyBtn = document.getElementById('copyMetadataBtn') as HTMLElement;
  const copyBtnText = document.getElementById('copyBtnText') as HTMLElement;

  try {
    await navigator.clipboard.writeText(metadataContent);
    copyBtnText.textContent = '✓ Copied!';
    setTimeout(() => { copyBtnText.textContent = '📋 Copy'; }, 2000);
  } catch (err) {
    console.error('Failed to copy:', err);
    copyBtnText.textContent = '✗ Failed';
    setTimeout(() => { copyBtnText.textContent = '📋 Copy'; }, 2000);
  }
}

function loadFile(file: File): void {
  currentFile = file;
  const name = file.name.toLowerCase();

  isPdfFile = file.type === 'application/pdf';
  isSvgFile = name.endsWith('.svg') || file.type === 'image/svg+xml';
  isBundle = name.endsWith('.pltz') || name.endsWith('.pltz.d') ||
             name.endsWith('.figz') || name.endsWith('.figz.d') ||
             name.endsWith('.statsz') || name.endsWith('.statsz.d');

  hideAllPreviews();

  if (isPdfFile) {
    loadPdf(file);
  } else if (isSvgFile) {
    loadSvg(file);
  } else if (isBundle) {
    loadBundle(file);
  } else {
    loadImage(file);
  }

  loadMetadata(file);
}

function hideAllPreviews(): void {
  imagePreview.style.display = 'none';
  svgPreview.style.display = 'none';
  pdfCanvas.style.display = 'none';
  pdfControls.style.display = 'none';
  singleFilePreview.style.display = 'block';
  bundleFiguresContainer.style.display = 'none';
  hideElement('bundleInfoSection');
}

function loadImage(file: File): void {
  const reader = new FileReader();
  reader.onload = (e) => {
    const img = new Image();
    img.onload = () => {
      currentImage = img;
      imagePreview.src = e.target?.result as string;
      imagePreview.style.display = 'block';
      pdfCanvas.style.display = 'none';
      pdfControls.style.display = 'none';
      uploadZone.style.display = 'none';
      contentArea.style.display = 'block';
      setText('previewTitle', 'Image Preview');
      hideElement('pdfPageCountRow');
      showElement('dpiAlert');

      currentDimensions = { width: img.width, height: img.height };
    };
    img.src = e.target?.result as string;
  };
  reader.readAsDataURL(file);
}

function loadSvg(file: File): void {
  const reader = new FileReader();
  reader.onload = (e) => {
    const svgContent = e.target?.result as string;
    svgPreview.innerHTML = svgContent;
    svgPreview.style.display = 'block';
    imagePreview.style.display = 'none';
    pdfCanvas.style.display = 'none';
    pdfControls.style.display = 'none';
    uploadZone.style.display = 'none';
    contentArea.style.display = 'block';
    setText('previewTitle', 'SVG Preview');
    hideElement('pdfPageCountRow');
    showElement('dpiAlert');
    setText('dpiAlert', 'SVG is a vector format. DPI applies when rasterizing.');

    const svgEl = svgPreview.querySelector('svg');
    if (svgEl) {
      const viewBox = svgEl.getAttribute('viewBox');
      const width = svgEl.getAttribute('width');
      const height = svgEl.getAttribute('height');

      if (viewBox) {
        const parts = viewBox.split(/\s+/);
        if (parts.length >= 4) {
          currentDimensions = { width: parseFloat(parts[2]), height: parseFloat(parts[3]), unit: 'viewBox' };
        }
      } else if (width && height) {
        currentDimensions = { width: parseFloat(width), height: parseFloat(height), unit: 'px' };
      }
    }
  };
  reader.readAsText(file);
}

function loadBundle(file: File): void {
  loadZipBundle(file, {
    singleFilePreview,
    bundleFiguresContainer,
    uploadZone,
    contentArea
  });
}

function loadFolderBundle(files: FileList): void {
  isBundle = true;
  const bundleState = loadFolderBundleImpl(
    files,
    {
      uploadZone,
      contentArea,
      singleFilePreview,
      bundleFiguresContainer
    },
    (dims) => {
      currentDimensions = dims;
      updatePhysicalSize();
    }
  );
  currentBundleFiles = bundleState.files;
  currentBundleType = bundleState.type;
}

function loadPdf(file: File): void {
  const reader = new FileReader();
  reader.onload = async (e) => {
    const typedArray = new Uint8Array(e.target?.result as ArrayBuffer);
    try {
      const pdf = await (window as any).pdfjsLib.getDocument(typedArray).promise;
      currentPdf = pdf;
      totalPdfPages = pdf.numPages;
      currentPdfPage = 1;

      imagePreview.style.display = 'none';
      pdfCanvas.style.display = 'block';
      pdfControls.style.display = 'block';
      uploadZone.style.display = 'none';
      contentArea.style.display = 'block';
      setText('previewTitle', 'PDF Preview');
      showElement('pdfPageCountRow');

      setText('totalPages', String(totalPdfPages));
      setText('pdfPageCount', String(totalPdfPages));

      const page = await pdf.getPage(1);
      const viewport = page.getViewport({ scale: 1 });
      currentDimensions = { width_pt: viewport.width, height_pt: viewport.height };

      await renderPdfPage(1);
    } catch (error) {
      console.error('Error loading PDF:', error);
      alert('Failed to load PDF file');
    }
  };
  reader.readAsArrayBuffer(file);
}

async function renderPdfPage(pageNum: number): Promise<void> {
  try {
    const page = await currentPdf.getPage(pageNum);
    const viewport = page.getViewport({ scale: 1.5 });
    const context = pdfCanvas.getContext('2d')!;
    pdfCanvas.height = viewport.height;
    pdfCanvas.width = viewport.width;
    await page.render({ canvasContext: context, viewport: viewport }).promise;
    setText('currentPage', String(pageNum));
    (document.getElementById('prevPage') as HTMLButtonElement).disabled = pageNum === 1;
    (document.getElementById('nextPage') as HTMLButtonElement).disabled = pageNum === totalPdfPages;
  } catch (error) {
    console.error('Error rendering PDF page:', error);
  }
}

function loadMetadata(file: File): void {
  showElement('metadataSection');
  setText('metadataStatus', 'Checking for embedded metadata...');
  setText('metadataContent', '');

  const formData = new FormData();
  formData.append('image', file);

  fetch('/api/read-image-metadata/', { method: 'POST', body: formData })
    .then(response => response.json())
    .then(data => {
      setText('fileName', file.name);
      setText('fileSize', formatFileSize(file.size));
      setText('fileType', data.file_type || file.type || 'Unknown');
      updateDimensionsFromResponse(data);
      displayMetadata(data);
    })
    .catch(error => {
      setText('metadataStatus', '✗ Error reading metadata');
      setStyle('metadataStatus', 'color', '#d32f2f');
      setText('metadataContent', `Error: ${error.message}`);
      setText('fileName', file.name);
      setText('fileSize', formatFileSize(file.size));
      setText('fileType', file.type || 'Unknown');
      if (currentDimensions) displayFallbackDimensions();
    });
}

function updateDimensionsFromResponse(data: any): void {
  if (data.file_type === 'pdf' && currentDimensions) {
    const widthPt = currentDimensions.width_pt!;
    const heightPt = currentDimensions.height_pt!;
    setText('pixelWidth', `${Math.round(widthPt)} pt`);
    setText('pixelHeight', `${Math.round(heightPt)} pt`);
    setText('aspectRatio', (widthPt / heightPt).toFixed(3));
    const widthInch = widthPt / 72;
    const heightInch = heightPt / 72;
    setText('widthMm', `${(widthInch * 25.4).toFixed(2)} mm`);
    setText('heightMm', `${(heightInch * 25.4).toFixed(2)} mm`);
    setText('widthInch', `${widthInch.toFixed(3)} in`);
    setText('heightInch', `${heightInch.toFixed(3)} in`);
    setText('usedDpi', '72 (PDF native)');
    showElement('dpiAlert');
    setText('dpiAlert', 'PDF uses vector graphics. DPI setting for rasterization only.');
    setText('dpiX', '72 dpi (native)');
    setText('dpiY', '72 dpi (native)');
  } else if (data.file_type === 'svg') {
    const dims = data.dimensions || currentDimensions || {};
    if (dims.width && dims.height) {
      setText('pixelWidth', `${dims.width.toFixed(2)} ${dims.unit || 'px'}`);
      setText('pixelHeight', `${dims.height.toFixed(2)} ${dims.unit || 'px'}`);
      setText('aspectRatio', (dims.width / dims.height).toFixed(3));
    }
    setText('dpiX', 'N/A (vector)');
    setText('dpiY', 'N/A (vector)');
  } else if (currentDimensions) {
    setText('pixelWidth', `${currentDimensions.width} px`);
    setText('pixelHeight', `${currentDimensions.height} px`);
    setText('aspectRatio', `${(currentDimensions.width! / currentDimensions.height!).toFixed(3)}`);
    updatePhysicalSize();
  }
}

function displayMetadata(data: any): void {
  if (data.has_metadata) {
    setText('metadataStatus', '✓ Metadata found');
    setStyle('metadataStatus', 'color', '#4a9b7e');
    setText('metadataContent', JSON.stringify(data.metadata, null, 2));
    showElement('copyMetadataBtn');
  } else {
    setText('metadataStatus', '○ No SciTeX metadata found');
    setStyle('metadataStatus', 'color', 'var(--text-secondary)');
    setText('metadataContent', data.message || 'This file does not contain embedded SciTeX metadata.');
    hideElement('copyMetadataBtn');
  }
}

function displayFallbackDimensions(): void {
  if (isPdfFile && currentDimensions) {
    setText('pixelWidth', `${Math.round(currentDimensions.width_pt!)} pt`);
    setText('pixelHeight', `${Math.round(currentDimensions.height_pt!)} pt`);
    setText('aspectRatio', (currentDimensions.width_pt! / currentDimensions.height_pt!).toFixed(3));
  } else if (currentDimensions) {
    setText('pixelWidth', `${currentDimensions.width} px`);
    setText('pixelHeight', `${currentDimensions.height} px`);
    setText('aspectRatio', (currentDimensions.width! / currentDimensions.height!).toFixed(3));
    updatePhysicalSize();
  }
}

function updatePhysicalSize(): void {
  if (!currentDimensions || isPdfFile || isSvgFile) return;
  const width = currentDimensions.width;
  const height = currentDimensions.height;
  if (!width || !height) return;

  const widthInch = width / currentDpi;
  const heightInch = height / currentDpi;
  setText('widthMm', `${(widthInch * 25.4).toFixed(2)} mm`);
  setText('heightMm', `${(heightInch * 25.4).toFixed(2)} mm`);
  setText('widthInch', `${widthInch.toFixed(3)} in`);
  setText('heightInch', `${heightInch.toFixed(3)} in`);
  setText('usedDpi', String(currentDpi));
  setText('dpiX', `${currentDpi} dpi`);
  setText('dpiY', `${currentDpi} dpi`);
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initImageViewer);
