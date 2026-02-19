/**
 * GallerySmartTruncation - Smart label truncation for gallery category buttons
 *
 * Extracted from GalleryCategories.ts for file-size compliance.
 * Truncates longer labels to ensure all buttons fit in the container,
 * progressing from text truncation to icon-only mode when space is very limited.
 */

/**
 * Setup smart label truncation for category buttons.
 * Truncates longer labels to ensure all buttons fit.
 * Can go all the way to icon-only mode when space is very limited.
 *
 * @param container - The gallery categories container element
 */
export function setupSmartTruncation(container: HTMLElement): void {
  // Store original labels
  const buttons = container.querySelectorAll(".category-btn");
  const originalLabels: Map<HTMLElement, string> = new Map();
  buttons.forEach((btn) => {
    const span = btn.querySelector("span");
    if (span) {
      originalLabels.set(btn as HTMLElement, span.textContent || "");
    }
  });

  // Truncation function
  const truncateLabels = () => {
    // Reset all labels first
    originalLabels.forEach((label, btn) => {
      const span = btn.querySelector("span") as HTMLElement;
      if (span) {
        span.textContent = label;
        span.style.display = "";
        span.removeAttribute("title");
      }
      btn.removeAttribute("title");
    });

    // Get container available width (excluding padding)
    const containerStyle = getComputedStyle(container);
    const containerPadding =
      parseFloat(containerStyle.paddingLeft) +
      parseFloat(containerStyle.paddingRight);
    const availableWidth = container.clientWidth - containerPadding;

    // Calculate total buttons width and gaps
    const gap = 4; // from CSS
    const buttonsArr = Array.from(buttons) as HTMLElement[];

    // Get width needed for each button
    const getButtonsWidth = () => {
      return buttonsArr.reduce((sum, btn, i) => {
        return sum + btn.offsetWidth + (i > 0 ? gap : 0);
      }, 0);
    };

    // If everything fits, done
    if (getButtonsWidth() <= availableWidth) return;

    // Phase 1: Truncate text progressively
    let maxIterations = 100;
    while (getButtonsWidth() > availableWidth && maxIterations-- > 0) {
      // Find the longest current label (that isn't already hidden)
      let longest: { btn: HTMLElement; span: HTMLElement; len: number } | null =
        null;
      for (const btn of buttonsArr) {
        const span = btn.querySelector("span") as HTMLElement;
        if (!span || span.style.display === "none") continue;
        const text = span.textContent || "";
        // Skip if already at minimum (2 chars + ...)
        if (text.endsWith("...") && text.length <= 5) continue;
        if (!longest || text.length > longest.len) {
          longest = { btn, span, len: text.length };
        }
      }

      if (!longest) break;

      // Truncate the longest
      const currentText = longest.span.textContent || "";
      const originalText = originalLabels.get(longest.btn) || currentText;

      if (currentText.endsWith("...")) {
        // Already truncated - shorten more
        const baseText = currentText.slice(0, -3);
        if (baseText.length > 2) {
          longest.span.textContent = baseText.slice(0, -1) + "...";
        }
      } else {
        // First truncation
        if (currentText.length > 3) {
          longest.span.textContent = currentText.slice(0, -1) + "...";
          longest.span.setAttribute("title", originalText);
          longest.btn.setAttribute("title", originalText);
        }
      }
    }

    // Phase 2: If still overflowing, start hiding text (icon-only mode)
    // Hide from longest to shortest original label
    if (getButtonsWidth() > availableWidth) {
      const buttonsByOriginalLength = [...buttonsArr].sort((a, b) => {
        const aLen = (originalLabels.get(a) || "").length;
        const bLen = (originalLabels.get(b) || "").length;
        return bLen - aLen; // longest first
      });

      for (const btn of buttonsByOriginalLength) {
        if (getButtonsWidth() <= availableWidth) break;

        const span = btn.querySelector("span") as HTMLElement;
        if (span && span.style.display !== "none") {
          const originalText = originalLabels.get(btn) || "";
          span.style.display = "none";
          btn.setAttribute("title", originalText);
        }
      }
    }
  };

  // Run on load and resize
  truncateLabels();
  window.addEventListener("resize", truncateLabels);

  // Also observe parent container for resize
  const resizeObserver = new ResizeObserver(() => {
    truncateLabels();
  });
  resizeObserver.observe(container);
}
