/**
 * DOM manipulation and query utilities
 */

/**
 * Safely query element from DOM
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/utils/dom.utils.ts loaded",
);
export function querySelector<T extends Element = Element>(
  selector: string,
): T | null {
  try {
    return document.querySelector(selector) as T | null;
  } catch (error) {
    console.error(`Failed to query selector: ${selector}`, error);
    return null;
  }
}

/**
 * Safely query all elements matching selector
 */
export function querySelectorAll<T extends Element = Element>(
  selector: string,
): T[] {
  try {
    return Array.from(document.querySelectorAll(selector)) as T[];
  } catch (error) {
    console.error(`Failed to query selector: ${selector}`, error);
    return [];
  }
}

/**
 * Set element's visibility
 */
export function setVisibility(
  element: HTMLElement | null,
  visible: boolean,
): void {
  if (!element) return;
  element.style.display = visible ? "" : "none";
}

/**
 * Toggle class on element
 */
export function toggleClass(
  element: HTMLElement | null,
  className: string,
  force?: boolean,
): void {
  if (!element) return;
  if (force === undefined) {
    element.classList.toggle(className);
  } else {
    element.classList.toggle(className, force);
  }
}

/**
 * Add class to element
 */
export function addClass(element: HTMLElement | null, className: string): void {
  if (!element) return;
  element.classList.add(className);
}

/**
 * Remove class from element
 */
export function removeClass(
  element: HTMLElement | null,
  className: string,
): void {
  if (!element) return;
  element.classList.remove(className);
}

/**
 * Check if element has class
 */
export function hasClass(
  element: HTMLElement | null,
  className: string,
): boolean {
  if (!element) return false;
  return element.classList.contains(className);
}

/**
 * Get computed style value
 */
export function getComputedStyle(element: HTMLElement): CSSStyleDeclaration {
  return window.getComputedStyle(element);
}

/**
 * Set multiple attributes on element
 */
export function setAttributes(
  element: HTMLElement | null,
  attributes: Record<string, string>,
): void {
  if (!element) return;
  Object.entries(attributes).forEach(([key, value]) => {
    element.setAttribute(key, value);
  });
}

/**
 * Remove element from DOM
 */
export function removeElement(element: HTMLElement | null): void {
  if (element?.parentNode) {
    element.parentNode.removeChild(element);
  }
}

/**
 * Clear element's content
 */
export function clearElement(element: HTMLElement | null): void {
  if (!element) return;
  element.innerHTML = "";
}

/**
 * Create element with options
 */
export function createElement(
  tag: string,
  options?: {
    className?: string | string[];
    id?: string;
    attributes?: Record<string, string>;
    textContent?: string;
    innerHTML?: string;
  },
): HTMLElement {
  const element = document.createElement(tag);

  if (options?.className) {
    if (Array.isArray(options.className)) {
      element.classList.add(...options.className);
    } else {
      element.className = options.className;
    }
  }

  if (options?.id) {
    element.id = options.id;
  }

  if (options?.attributes) {
    setAttributes(element, options.attributes);
  }

  if (options?.textContent) {
    element.textContent = options.textContent;
  }

  if (options?.innerHTML) {
    element.innerHTML = options.innerHTML;
  }

  return element;
}

/**
 * Scroll element into view smoothly
 */
export function scrollIntoView(
  element: HTMLElement | null,
  behavior: "smooth" | "auto" = "smooth",
): void {
  if (element) {
    element.scrollIntoView({ behavior, block: "nearest" });
  }
}

/**
 * Get scroll position
 */
export function getScrollPosition(): { x: number; y: number } {
  return {
    x: window.scrollX || document.documentElement.scrollLeft,
    y: window.scrollY || document.documentElement.scrollTop,
  };
}

/**
 * Set scroll position
 */
export function setScrollPosition(x: number, y: number): void {
  window.scrollTo(x, y);
}
