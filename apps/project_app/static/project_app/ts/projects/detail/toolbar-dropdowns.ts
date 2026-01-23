/**
 * Toolbar Dropdown Handlers
 * Manages branch, add-file, code, and copy dropdown menus
 */

export function toggleBranchDropdown(): void {
  const dropdown = document.getElementById(
    "branch-dropdown",
  ) as HTMLElement | null;
  const isVisible = dropdown && dropdown.style.display === "block";

  closeAllDropdowns();

  if (dropdown) {
    dropdown.style.display = isVisible ? "none" : "block";
    console.log("Branch dropdown toggled:", dropdown.style.display);
  }
}

export function switchBranch(branchName: string): void {
  console.log("Switching to branch:", branchName);
  const currentBranch = document.getElementById("current-branch");
  if (currentBranch) currentBranch.textContent = branchName;

  // Update active state in dropdown
  document.querySelectorAll(".branch-item").forEach((item: Element) => {
    const htmlItem = item as HTMLElement;
    if (htmlItem.dataset.branch === branchName) {
      htmlItem.classList.add("active");
      const svg = htmlItem.querySelector("svg") as SVGElement | null;
      if (svg) svg.style.opacity = "1";
    } else {
      htmlItem.classList.remove("active");
      const svg = htmlItem.querySelector("svg") as SVGElement | null;
      if (svg) svg.style.opacity = "0";
    }
  });

  // Close dropdown
  const branchDropdown = document.getElementById(
    "branch-dropdown",
  ) as HTMLElement | null;
  if (branchDropdown) branchDropdown.style.display = "none";

  // TODO: Reload page with selected branch
}

export function toggleAddFileDropdown(): void {
  const dropdown = document.getElementById(
    "add-file-dropdown",
  ) as HTMLElement | null;
  if (!dropdown) return;

  const isVisible = dropdown.style.display === "block";

  closeAllDropdowns();

  dropdown.style.display = isVisible ? "none" : "block";
  console.log("Add file dropdown toggled:", dropdown.style.display);
}

export function toggleCodeDropdown(): void {
  const dropdown = document.getElementById(
    "code-dropdown",
  ) as HTMLElement | null;
  if (!dropdown) return;

  const isVisible = dropdown.style.display === "block";

  closeAllDropdowns();

  dropdown.style.display = isVisible ? "none" : "block";
  console.log("Code dropdown toggled:", dropdown.style.display);
}

export function toggleCopyDropdown(): void {
  const dropdown = document.getElementById(
    "copy-dropdown",
  ) as HTMLElement | null;
  if (!dropdown) return;

  const isVisible = dropdown.style.display === "block";

  closeAllDropdowns();

  dropdown.style.display = isVisible ? "none" : "block";
  console.log("Copy dropdown toggled:", dropdown.style.display);
}

export function closeAllDropdowns(): void {
  const dropdowns = [
    "branch-dropdown-menu",
    "add-file-dropdown",
    "code-dropdown",
    "copy-dropdown",
  ];
  dropdowns.forEach((id) => {
    const dropdown = document.getElementById(id) as HTMLElement | null;
    if (dropdown && dropdown.style.display === "block") {
      dropdown.style.display = "none";
    }
  });
}
