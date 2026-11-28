/** Remove application controls with their contents before static sanitization. */
export function removeExportControls(content: ParentNode): void {
  content.querySelectorAll("button,input,textarea,select,.docs-section-export,.docs-toolbar,.docs-context-menu,[data-docs-html-status]")
    .forEach(node => node.remove());
}
