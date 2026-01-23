/**
 * Preview Navigation Module
 * Handles preview panel visibility and navigation
 *
 * @version 2.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/editor/preview-panel/navigation.ts loaded",
);

export class PreviewNavigation {
  private previewPanel: HTMLElement;
  private togglePreviewBtn: HTMLButtonElement;
  private previewVisible: boolean = true;

  constructor(previewPanel: HTMLElement, togglePreviewBtn: HTMLButtonElement) {
    this.previewPanel = previewPanel;
    this.togglePreviewBtn = togglePreviewBtn;
    this.setupEventListeners();
  }

  /**
   * Setup event listeners
   */
  private setupEventListeners(): void {
    if (this.togglePreviewBtn) {
      this.togglePreviewBtn.addEventListener("click", () => {
        this.togglePreview();
      });
    }
  }

  /**
   * Toggle preview panel visibility
   */
  togglePreview(): void {
    this.previewVisible = !this.previewVisible;
    this.previewPanel.style.display = this.previewVisible ? "flex" : "none";
    this.togglePreviewBtn.innerHTML = this.previewVisible
      ? '<i class="fas fa-eye-slash me-1"></i>Hide Preview'
      : '<i class="fas fa-eye me-1"></i>Show Preview';
  }

  /**
   * Get current visibility state
   */
  isVisible(): boolean {
    return this.previewVisible;
  }

  /**
   * Show preview panel
   */
  show(): void {
    if (!this.previewVisible) {
      this.togglePreview();
    }
  }

  /**
   * Hide preview panel
   */
  hide(): void {
    if (this.previewVisible) {
      this.togglePreview();
    }
  }
}
