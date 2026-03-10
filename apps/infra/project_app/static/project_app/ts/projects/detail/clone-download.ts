/**
 * Clone and Download Handlers
 * Handles clone URL copying and project ZIP downloads
 */

export function copyCloneUrl(event: Event): void {
  const input = document.getElementById("clone-url") as HTMLInputElement;
  if (!input) return;

  navigator.clipboard
    .writeText(input.value)
    .then(() => {
      const btn = (event.target as HTMLElement).closest("button");
      if (!btn) return;

      const originalHTML = btn.innerHTML;
      btn.innerHTML =
        '<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z"/></svg>';
      setTimeout(() => {
        btn.innerHTML = originalHTML;
      }, 2000);
    })
    .catch((err: Error) => {
      console.error("Failed to copy:", err);
    });
}

export function downloadProjectZip(): void {
  // Placeholder for ZIP download functionality
  alert("ZIP download functionality coming soon!");
}
