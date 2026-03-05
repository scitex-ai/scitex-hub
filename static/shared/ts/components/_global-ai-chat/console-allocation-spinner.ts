/** Overlay spinner shown during SLURM allocation on the terminal container. */

export function showAllocationSpinner(el: HTMLElement): void {
  if (el.querySelector(".scitex-allocation-overlay")) return;
  const o = document.createElement("div");
  o.className = "scitex-allocation-overlay";
  o.innerHTML =
    '<div class="scitex-allocation-spinner"><i class="fas fa-circle-notch fa-spin"></i><span>Starting computing environment...</span></div>';
  el.style.position = "relative";
  el.appendChild(o);
}

export function hideAllocationSpinner(el: HTMLElement): void {
  el.querySelector(".scitex-allocation-overlay")?.remove();
}
