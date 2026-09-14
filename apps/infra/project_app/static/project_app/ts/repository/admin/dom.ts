/**
 * Tiny DOM-building helper for the Project Health page.
 *
 * Text always goes through textContent, so translated strings and
 * server-supplied names can never be reinterpreted as HTML.
 *
 * @module repository/admin/dom
 */

export interface ElementOptions {
  className?: string;
  text?: string;
  style?: string;
  attrs?: Record<string, string>;
}

export function createEl<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  options: ElementOptions = {},
  children: Node[] = [],
): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  if (options.className) {
    el.className = options.className;
  }
  if (options.text !== undefined) {
    el.textContent = options.text;
  }
  if (options.style) {
    el.style.cssText = options.style;
  }
  if (options.attrs) {
    for (const [name, value] of Object.entries(options.attrs)) {
      el.setAttribute(name, value);
    }
  }
  for (const child of children) {
    el.appendChild(child);
  }
  return el;
}

/** Monospace block used by every confirmation dialog to show the name. */
export const DIALOG_NAME_STYLE =
  "margin: 1rem 0; font-family: monospace; background: var(--color-canvas-subtle); padding: 0.5rem; border-radius: 0.25rem; word-break: break-all;";

/** A paragraph "<strong>label</strong> text" built without innerHTML. */
export function labelledParagraph(label: string, text: string): HTMLElement {
  return createEl("p", {}, [
    createEl("strong", { text: label }),
    document.createTextNode(" " + text),
  ]);
}
