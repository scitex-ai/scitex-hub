/**
 * PDF Navigation
 * Handles page navigation and page change tracking
 */

console.log("[DEBUG] PDFNavigation.ts loaded");

export class PDFNavigation {
  private currentPage: number = 1;
  private onPageChangeCallback?: (pageNum: number) => void;

  constructor(onPageChange?: (pageNum: number) => void) {
    this.onPageChangeCallback = onPageChange;
  }

  /**
   * Go to specific page
   */
  gotoPage(pageNum: number, totalPages: number): void {
    if (pageNum < 1 || pageNum > totalPages) return;

    this.currentPage = pageNum;
    const pageElement = document.getElementById(`pdfjs-page-${pageNum}`);
    if (pageElement) {
      pageElement.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  /**
   * Go to next page
   */
  nextPage(totalPages: number): void {
    if (this.currentPage < totalPages) {
      this.gotoPage(this.currentPage + 1, totalPages);
    }
  }

  /**
   * Go to previous page
   */
  prevPage(): void {
    if (this.currentPage > 1) {
      this.gotoPage(this.currentPage - 1, this.currentPage);
    }
  }

  /**
   * Update current page based on scroll position
   */
  updateCurrentPageFromScroll(viewer: HTMLElement): void {
    const pages = Array.from(viewer.querySelectorAll(".pdfjs-page-container"));
    const scrollTop = viewer.scrollTop;
    const viewportMiddle = scrollTop + viewer.clientHeight / 3;

    for (const page of pages) {
      const pageElement = page as HTMLElement;
      const pageTop = pageElement.offsetTop;
      const pageBottom = pageTop + pageElement.offsetHeight;

      if (viewportMiddle >= pageTop && viewportMiddle < pageBottom) {
        const pageNumStr = pageElement.dataset.pageNum;
        if (pageNumStr) {
          const pageNum = parseInt(pageNumStr);
          if (pageNum !== this.currentPage) {
            this.currentPage = pageNum;
            if (this.onPageChangeCallback) {
              this.onPageChangeCallback(pageNum);
            }
            console.log("[PDFNavigation] Current page:", pageNum);
          }
        }
        break;
      }
    }
  }

  /**
   * Setup scroll listener for page tracking
   */
  setupScrollListener(viewer: HTMLElement): void {
    let scrollTimeout: number;

    viewer.addEventListener("scroll", () => {
      clearTimeout(scrollTimeout);
      scrollTimeout = window.setTimeout(() => {
        this.updateCurrentPageFromScroll(viewer);
      }, 100);
    });

    console.log("[PDFNavigation] Scroll listener attached");
  }

  /**
   * Get current page
   */
  getCurrentPage(): number {
    return this.currentPage;
  }

  /**
   * Set current page (without scrolling)
   */
  setCurrentPage(pageNum: number): void {
    this.currentPage = pageNum;
  }
}

// EOF
