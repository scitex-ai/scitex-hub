/**
 * File Upload Module
 *
 * Handles BibTeX file upload via drag-and-drop and file selection,
 * including visual feedback and auto-submission.
 *
 * @module file-upload
 */

/**
 * File upload configuration
 */
export interface FileUploadConfig {
  formId: string;
  fileInputId: string;
  dropZoneId: string;
  onFileSelected?: (file: File) => void;
  onSubmit?: (formData: FormData) => void;
}

/**
 * File upload manager class
 */
export class FileUploadManager {
  private form: HTMLFormElement;
  private fileInput: HTMLInputElement;
  private dropZone: HTMLElement;
  private dragCounter: number = 0;
  private config: FileUploadConfig;

  constructor(config: FileUploadConfig) {
    this.config = config;

    const form = document.getElementById(config.formId) as HTMLFormElement;
    const fileInput = document.getElementById(
      config.fileInputId,
    ) as HTMLInputElement;
    const dropZone = document.getElementById(config.dropZoneId) as HTMLElement;

    if (!form || !fileInput || !dropZone) {
      throw new Error("[FileUpload] Required elements not found");
    }

    this.form = form;
    this.fileInput = fileInput;
    this.dropZone = dropZone;

    this.initializeDragAndDrop();
    this.initializeFileInput();
    this.preventManualSubmit();
  }

  /**
   * Initialize drag and drop handlers
   */
  private initializeDragAndDrop(): void {
    // Prevent default drag behaviors
    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
      this.dropZone.addEventListener(
        eventName,
        this.preventDefaults.bind(this),
        false,
      );
    });

    // Dragenter: increment counter and apply styles
    this.dropZone.addEventListener("dragenter", this.handleDragEnter.bind(this));

    // Dragover: maintain styles
    this.dropZone.addEventListener("dragover", this.handleDragOver.bind(this));

    // Dragleave: decrement counter, remove styles only when truly leaving
    this.dropZone.addEventListener("dragleave", this.handleDragLeave.bind(this));

    // Drop: reset counter and remove styles
    this.dropZone.addEventListener("drop", this.handleDrop.bind(this));
  }

  /**
   * Initialize file input change handler
   */
  private initializeFileInput(): void {
    this.fileInput.addEventListener("change", () => {
      if (this.fileInput.files && this.fileInput.files.length > 0) {
        this.showFileName(this.fileInput.files[0].name);
      }
    });
  }

  /**
   * Prevent manual form submission
   */
  private preventManualSubmit(): void {
    this.form.addEventListener("submit", (e: Event) => {
      e.preventDefault();
    });
  }

  /**
   * Prevent default event behaviors
   */
  private preventDefaults(e: Event): void {
    e.preventDefault();
    e.stopPropagation();
  }

  /**
   * Handle drag enter event
   */
  private handleDragEnter(e: DragEvent): void {
    this.dragCounter++;
    if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
    this.applyDragStyles();
  }

  /**
   * Handle drag over event
   */
  private handleDragOver(e: DragEvent): void {
    if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
  }

  /**
   * Handle drag leave event
   */
  private handleDragLeave(): void {
    this.dragCounter--;
    if (this.dragCounter === 0) {
      this.resetDropZoneStyle();
    }
  }

  /**
   * Handle drop event
   */
  private handleDrop(e: DragEvent): void {
    this.dragCounter = 0;
    this.resetDropZoneStyle();

    const dt = e.dataTransfer;
    const files = dt?.files;

    if (files && files.length > 0) {
      const file = files[0];
      if (file.name.endsWith(".bib")) {
        // Assign the dropped file to the input
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        this.fileInput.files = dataTransfer.files;

        // Update visual feedback
        this.showFileName(file.name);
      } else {
        alert("Please drop a .bib file");
      }
    }
  }

  /**
   * Apply drag-over styling to drop zone
   */
  private applyDragStyles(): void {
    this.dropZone.style.borderColor = "#6B8FB3";
    this.dropZone.style.borderStyle = "solid";
    this.dropZone.style.background = "rgba(107, 143, 179, 0.15)";
    this.dropZone.style.transform = "scale(1.01)";
    this.dropZone.style.boxShadow = "0 4px 16px rgba(107, 143, 179, 0.3)";
  }

  /**
   * Reset drop zone styling
   */
  private resetDropZoneStyle(): void {
    this.dropZone.style.borderColor = "var(--scitex-color-03)";
    this.dropZone.style.borderStyle = "dashed";
    this.dropZone.style.background = "var(--color-canvas-subtle)";
    this.dropZone.style.transform = "scale(1)";
    this.dropZone.style.boxShadow = "none";
  }

  /**
   * Display file name and trigger auto-submit
   */
  private showFileName(fileName: string): void {
    const uploadMessage = document.getElementById("uploadMessage");
    const fileNameDisplay = document.getElementById("fileNameDisplay");
    const fileNameEl = document.getElementById("fileName");

    if (uploadMessage) uploadMessage.style.display = "none";
    if (fileNameDisplay) fileNameDisplay.style.display = "block";
    if (fileNameEl) fileNameEl.textContent = fileName;

    // Add success visual feedback to drop zone
    this.dropZone.style.borderColor = "var(--info-color)";
    this.dropZone.style.background = "rgba(107, 143, 179, 0.1)";

    // Notify parent if callback provided
    if (this.config.onFileSelected && this.fileInput.files) {
      this.config.onFileSelected(this.fileInput.files[0]);
    }

    // Auto-submit after short delay
    setTimeout(() => {
      this.autoSubmit();
    }, 300);
  }

  /**
   * Auto-submit the form
   */
  private autoSubmit(): void {
    const formData = new FormData(this.form);

    // Show processing state
    this.dropZone.style.borderColor = "var(--info-color)";
    this.dropZone.style.background = "rgba(107, 143, 179, 0.15)";

    // Show progress area
    const progressArea = document.getElementById("bibtexProgressArea");
    if (progressArea) progressArea.style.display = "block";

    // Notify parent if callback provided
    if (this.config.onSubmit) {
      this.config.onSubmit(formData);
    }
  }

  /**
   * Get form data
   */
  public getFormData(): FormData {
    return new FormData(this.form);
  }

  /**
   * Reset the form
   */
  public reset(): void {
    this.form.reset();
    this.resetDropZoneStyle();

    const uploadMessage = document.getElementById("uploadMessage");
    const fileNameDisplay = document.getElementById("fileNameDisplay");

    if (uploadMessage) uploadMessage.style.display = "block";
    if (fileNameDisplay) fileNameDisplay.style.display = "none";
  }
}
