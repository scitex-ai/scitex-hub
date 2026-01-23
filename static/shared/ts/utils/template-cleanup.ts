/**
 * Template Cleanup Utility
 *
 * Removes stray Django template text nodes caused by linter reformatting
 * global_base.html. This is a workaround until the linter configuration
 * is fixed to not merge Django template tags onto single lines.
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

// Run immediately when script loads
cleanupTemplateText();

// Run again after DOM is fully loaded
document.addEventListener("DOMContentLoaded", cleanupTemplateText);

// Run once more after a short delay to catch any late additions
setTimeout(cleanupTemplateText, 100);

console.log("[DEBUG] template-cleanup.ts loaded");
