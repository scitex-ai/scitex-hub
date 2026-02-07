/**
 * Modal Manager
 * Centralized system for managing modals (dialog boxes/popups)
 * Provides consistent behavior: ESC to close, backdrop click, copy functionality
 */

export interface ModalConfig {
  title: string;
  content: string;
  showCopyButton?: boolean;
  showPrintButton?: boolean;
  maxWidth?: string;
  onClose?: () => void;
}

export class ModalManager {
  private activeModal: HTMLElement | null = null;

  /**
   * Show a modal with the given configuration
   */
  showModal(config: ModalConfig): void {
    // Close any existing modal first
    this.closeModal();

    // Create modal structure
    const overlay = this.createModalOverlay();
    const modal = this.createModalDialog(config);

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // Animate in
    requestAnimationFrame(() => {
      overlay.classList.add("active");
    });

    this.activeModal = overlay;

    // Setup event listeners
    this.setupModalListeners(overlay, config);
  }

  /**
   * Close the active modal
   */
  closeModal(): void {
    if (!this.activeModal) return;

    this.activeModal.classList.remove("active");

    // Wait for animation to finish before removing
    setTimeout(() => {
      this.activeModal?.remove();
      this.activeModal = null;
    }, 200);
  }

  /**
   * Create modal overlay (backdrop)
   */
  private createModalOverlay(): HTMLElement {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    return overlay;
  }

  /**
   * Create modal dialog content
   */
  private createModalDialog(config: ModalConfig): HTMLElement {
    const dialog = document.createElement("div");
    dialog.className = "modal-dialog";
    if (config.maxWidth) {
      dialog.style.maxWidth = config.maxWidth;
    }

    // Header
    const header = document.createElement("div");
    header.className = "modal-header";

    const title = document.createElement("span");
    title.className = "modal-title";
    title.innerHTML = config.title;

    const closeBtn = document.createElement("button");
    closeBtn.className = "modal-close-btn";
    closeBtn.innerHTML = "×";
    closeBtn.onclick = () => this.closeModal();

    header.appendChild(title);
    header.appendChild(closeBtn);

    // Body
    const body = document.createElement("div");
    body.className = "modal-body";
    body.innerHTML = config.content;

    // Footer
    const footer = document.createElement("div");
    footer.className = "modal-footer";

    if (config.showCopyButton) {
      const copyBtn = document.createElement("button");
      copyBtn.className = "modal-btn modal-btn-secondary";
      copyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy';
      copyBtn.onclick = () => this.copyModalContent(body);
      footer.appendChild(copyBtn);
    }

    if (config.showPrintButton) {
      const printBtn = document.createElement("button");
      printBtn.className = "modal-btn modal-btn-secondary";
      printBtn.innerHTML = '<i class="fas fa-print"></i> Print';
      printBtn.onclick = () => this.printModalContent(config.title, body);
      footer.appendChild(printBtn);
    }

    const closeFooterBtn = document.createElement("button");
    closeFooterBtn.className = "modal-btn modal-btn-primary";
    closeFooterBtn.textContent = "Close";
    closeFooterBtn.onclick = () => this.closeModal();
    footer.appendChild(closeFooterBtn);

    // Assemble dialog
    dialog.appendChild(header);
    dialog.appendChild(body);
    dialog.appendChild(footer);

    return dialog;
  }

  /**
   * Setup event listeners for modal
   */
  private setupModalListeners(overlay: HTMLElement, config: ModalConfig): void {
    // ESC key to close
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        this.closeModal();
        if (config.onClose) config.onClose();
        document.removeEventListener("keydown", handleEscape);
      }
    };
    document.addEventListener("keydown", handleEscape);

    // Backdrop click to close
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        this.closeModal();
        if (config.onClose) config.onClose();
      }
    });
  }

  /**
   * Copy modal content to clipboard
   */
  private async copyModalContent(bodyElement: HTMLElement): Promise<void> {
    try {
      // Extract text content, preserving structure
      const text = this.extractTextContent(bodyElement);

      await navigator.clipboard.writeText(text);

      // Show feedback
      this.showCopyFeedback();
    } catch (error) {
      console.error("[ModalManager] Failed to copy:", error);
      alert("Failed to copy to clipboard");
    }
  }

  /**
   * Extract readable text from modal content
   */
  private extractTextContent(element: HTMLElement): string {
    // Clone to avoid modifying original
    const clone = element.cloneNode(true) as HTMLElement;

    // Process kbd elements
    clone.querySelectorAll("kbd").forEach((kbd) => {
      kbd.textContent = `[${kbd.textContent}]`;
    });

    // Process headings
    clone.querySelectorAll("h3, h4").forEach((heading) => {
      heading.textContent = `\n${heading.textContent}\n${"=".repeat(heading.textContent?.length || 0)}`;
    });

    // Process lists
    clone.querySelectorAll("li").forEach((li) => {
      li.textContent = `  • ${li.textContent}`;
    });

    return clone.textContent || "";
  }

  /**
   * Show temporary "Copied!" feedback
   */
  private showCopyFeedback(): void {
    const feedback = document.createElement("div");
    feedback.className = "copy-feedback";
    feedback.textContent = "✓ Copied to clipboard!";
    feedback.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: var(--workspace-icon-primary);
      color: white;
      padding: 12px 20px;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      z-index: 100000;
      animation: slideInUp 0.3s ease;
    `;

    document.body.appendChild(feedback);

    setTimeout(() => {
      feedback.style.animation = "slideOutDown 0.3s ease";
      setTimeout(() => feedback.remove(), 300);
    }, 2000);
  }

  /**
   * Print modal content
   */
  private printModalContent(title: string, bodyElement: HTMLElement): void {
    // Create a print window
    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      alert("Please allow popups to print");
      return;
    }

    // Clone the content
    const content = bodyElement.cloneNode(true) as HTMLElement;

    // Generate print-friendly HTML
    const printHTML = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>${title}</title>
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
          }
          h3, h4 {
            color: #1a2a40;
            margin-top: 20px;
            border-bottom: 2px solid #e1e8ed;
            padding-bottom: 8px;
          }
          ul {
            list-style: none;
            padding-left: 0;
          }
          li {
            padding: 6px 0;
            border-bottom: 1px solid #f0f0f0;
          }
          kbd {
            background: #f6f8fa;
            border: 1px solid #d0d7de;
            border-radius: 3px;
            padding: 2px 6px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 90%;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
          }
          th, td {
            border: 1px solid #d0d7de;
            padding: 8px;
            text-align: left;
          }
          th {
            background: #f6f8fa;
            font-weight: 600;
          }
          @media print {
            body { padding: 0; }
          }
        </style>
      </head>
      <body>
        <h1>${title}</h1>
        ${content.innerHTML}
      </body>
      </html>
    `;

    printWindow.document.write(printHTML);
    printWindow.document.close();

    // Wait for content to load, then print
    printWindow.onload = () => {
      printWindow.print();
      // Close after printing (or if cancelled)
      printWindow.onafterprint = () => printWindow.close();
    };
  }
}

// Global modal manager instance
export const modalManager = new ModalManager();
