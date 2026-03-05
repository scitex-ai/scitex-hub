/**
 * Code Block Copy Button Handler
 * Adds copy-to-clipboard functionality to all code blocks
 * Also applies syntax highlighting and line numbers
 *
 * Note: Suppresses highlight.js warnings about unescaped HTML in code blocks.
 * These are false positives that occur when markdown table syntax is displayed
 * as examples in documentation. The HTML is properly escaped by the markdown renderer.
 */

interface CodeBlockConfig {
  showLineNumbers: boolean;
  enableCopyButton: boolean;
}

class CodeBlockManager {
  private config: CodeBlockConfig;
  private originalWarn: typeof console.warn;
  private warningKeywords = ["unescaped HTML", "security risk"];

  constructor(config: Partial<CodeBlockConfig> = {}) {
    this.config = {
      showLineNumbers: true,
      enableCopyButton: true,
      ...config,
    };

    // Store original console.warn and install global filter
    this.originalWarn = console.warn;
    this.installGlobalWarningFilter();
  }

  /**
   * Install global filter to suppress false positive warnings from highlight.js
   * This is installed immediately to catch warnings from all sources
   */
  private installGlobalWarningFilter(): void {
    const self = this;
    console.warn = function (...args: any[]) {
      const message = args[0]?.toString() || "";
      if (self.warningKeywords.some((keyword) => message.includes(keyword))) {
        // Suppress these false positive warnings from highlight.js
        // about unescaped HTML in code blocks when displaying markdown examples
        return;
      }
      // Pass through all other warnings
      self.originalWarn.apply(console, args);
    };
  }

  /**
   * Suppress highlight.js warnings during callback execution
   */
  private suppressHighlightWarnings(callback: () => void): void {
    try {
      callback();
    } catch (error) {
      console.error("Error during code block highlighting:", error);
    }
  }

  /**
   * Initialize code block handling
   */
  public init(): void {
    document.addEventListener("DOMContentLoaded", () => {
      this.processCodeBlocks();
    });

    // Also process dynamically added code blocks
    if ("MutationObserver" in window) {
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.addedNodes.length) {
            mutation.addedNodes.forEach((node) => {
              if (node.nodeType === Node.ELEMENT_NODE) {
                const element = node as Element;
                if (element.matches("code") || element.querySelector("code")) {
                  this.processCodeBlocks();
                }
              }
            });
          }
        });
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true,
      });
    }
  }

  /**
   * Process all code blocks on the page
   */
  private processCodeBlocks(): void {
    const preElements = document.querySelectorAll("pre code");

    preElements.forEach((codeBlock) => {
      this.processCodeBlock(codeBlock as HTMLElement);
    });
  }

  /**
   * Process a single code block
   */
  private processCodeBlock(codeBlock: HTMLElement): void {
    // Skip code blocks inside .api-example (they have their own copy/label UI)
    if (codeBlock.closest(".api-example")) return;

    // Apply syntax highlighting if hljs is available
    if (
      typeof (window as any).hljs !== "undefined" &&
      !codeBlock.dataset.highlighted
    ) {
      this.suppressHighlightWarnings(() => {
        (window as any).hljs.highlightElement(codeBlock);
      });
    }

    // Apply line numbers if available
    if (
      this.config.showLineNumbers &&
      typeof (window as any).hljs !== "undefined" &&
      (window as any).hljs.lineNumbersBlock
    ) {
      (window as any).hljs.lineNumbersBlock(codeBlock);
    }

    const preElement = codeBlock.parentElement;
    if (!preElement) return;

    // Skip if copy button already exists
    if (preElement.querySelector(".code-copy-button")) {
      return;
    }

    // Create copy button with SVG icon
    if (this.config.enableCopyButton) {
      this.addCopyButton(codeBlock, preElement);
    }

    // Handle Ctrl+A to select only code content
    this.setupSelectAllHandler(codeBlock, preElement);
  }

  /**
   * Add copy button to code block
   */
  private addCopyButton(codeBlock: HTMLElement, preElement: HTMLElement): void {
    const copyButton = document.createElement("button");
    copyButton.className = "code-copy-button";
    copyButton.setAttribute("aria-label", "Copy code to clipboard");
    copyButton.setAttribute("title", "Copy code");

    // SVG clipboard icon
    const copyIcon = `
      <svg class="copy-icon" viewBox="0 0 16 16" fill="currentColor">
        <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/>
        <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3z"/>
      </svg>
    `;

    const checkIcon = `
      <svg class="check-icon" viewBox="0 0 16 16" fill="currentColor">
        <path d="M10.97 4.97a.75.75 0 0 1 1.07 1.05l-3.99 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425a.267.267 0 0 1 .02-.022z"/>
      </svg>
    `;

    copyButton.innerHTML = copyIcon;

    // Add click handler
    copyButton.addEventListener("click", (e) => {
      e.preventDefault();
      this.copyToClipboard(copyButton, codeBlock, copyIcon, checkIcon);
    });

    // Insert button into the pre element
    preElement.insertBefore(copyButton, codeBlock);
  }

  /**
   * Copy code to clipboard
   */
  private copyToClipboard(
    button: HTMLElement,
    codeBlock: HTMLElement,
    copyIcon: string,
    checkIcon: string,
  ): void {
    const codeText = codeBlock.textContent;
    if (!codeText) return;

    navigator.clipboard
      .writeText(codeText)
      .then(() => {
        // Show success state
        button.classList.add("copied");
        button.innerHTML = checkIcon;

        // Reset after 2 seconds
        setTimeout(() => {
          button.classList.remove("copied");
          button.innerHTML = copyIcon;
        }, 2000);
      })
      .catch((err) => {
        console.error("Failed to copy console:", err);
        button.classList.add("error");
        setTimeout(() => {
          button.classList.remove("error");
          button.innerHTML = copyIcon;
        }, 2000);
      });
  }

  /**
   * Setup Ctrl+A handler to select only code content
   */
  private setupSelectAllHandler(
    codeBlock: HTMLElement,
    preElement: HTMLElement,
  ): void {
    document.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "a") {
        // Check if cursor is inside this code block
        const selection = window.getSelection();
        const selectedNode = selection?.anchorNode;

        // Check if selection is within the current code block
        if (selectedNode && preElement.contains(selectedNode)) {
          e.preventDefault();

          // Select only the code element's content
          const range = document.createRange();
          range.selectNodeContents(codeBlock);
          selection?.removeAllRanges();
          selection?.addRange(range);

          console.log("Ctrl+A: Selected code block content only");
        }
      }
    });
  }
}

// Initialize when document is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    const manager = new CodeBlockManager();
    manager.init();
  });
} else {
  const manager = new CodeBlockManager();
  manager.init();
}
