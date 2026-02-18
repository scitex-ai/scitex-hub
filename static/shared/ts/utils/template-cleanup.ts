/**
 * Template Cleanup Utility
 *
 * Removes stray Django template text nodes caused by linter reformatting
 * global_base.html, and trims whitespace from terminal-log elements
 * whose pre-wrap style preserves template indentation.
 */

function cleanupTemplateText(): void {
  const body = document.body;
  const childNodes = Array.from(body.childNodes);
  childNodes.forEach((node) => {
    if (node.nodeType === Node.TEXT_NODE && node.textContent?.includes("{%")) {
      node.remove();
    }
  });
}

function trimTerminalLogs(): void {
  document.querySelectorAll<HTMLElement>(".terminal-log").forEach((el) => {
    if (el.children.length === 0 && el.textContent) {
      el.textContent = el.textContent.replace(/\s+/g, " ").trim();
    }
  });
}

// Run immediately when script loads
cleanupTemplateText();

// Run again after DOM is fully loaded
document.addEventListener("DOMContentLoaded", () => {
  cleanupTemplateText();
  trimTerminalLogs();
});

// Run once more after a short delay to catch any late additions
setTimeout(cleanupTemplateText, 100);
