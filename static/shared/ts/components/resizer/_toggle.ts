/**
 * Toggle button icon sync for the Resizer system.
 * Handles flipping chevron icons when panels collapse/expand.
 */

/** Icon flip mapping: when a panel collapses, the icon flips direction */
const FLIP_MAP: Record<string, string> = {
  "fa-chevron-left": "fa-chevron-right",
  "fa-chevron-right": "fa-chevron-left",
  "fa-chevron-up": "fa-chevron-down",
  "fa-chevron-down": "fa-chevron-up",
  "fa-angles-left": "fa-angles-right",
  "fa-angles-right": "fa-angles-left",
  "fa-angles-up": "fa-angles-down",
  "fa-angles-down": "fa-angles-up",
};

/**
 * Update the toggle button icon based on collapsed state.
 * When collapsed, the icon flips to show the "expand" direction.
 */
export function updateToggleIcon(
  toggleEl: HTMLElement,
  expandedIcon: string,
  isCollapsed: boolean,
): void {
  const icon = toggleEl.querySelector("i");
  if (!icon) return;

  const collapsedIcon = FLIP_MAP[expandedIcon] || expandedIcon;

  // Remove both states
  icon.classList.remove(expandedIcon, collapsedIcon);
  // Apply current state
  icon.classList.add(isCollapsed ? collapsedIcon : expandedIcon);
}

/**
 * Create a toggle button element inside the resizer handle.
 * Returns the created button element.
 */
export function createToggleButton(
  resizerEl: HTMLElement,
  icon: string,
  title: string,
): HTMLElement {
  const btn = document.createElement("button");
  btn.className = "resizer-toggle-btn";
  btn.title = title;
  btn.setAttribute("aria-label", title);

  const iconEl = document.createElement("i");
  iconEl.className = `fas ${icon}`;
  btn.appendChild(iconEl);

  resizerEl.appendChild(btn);
  return btn;
}
