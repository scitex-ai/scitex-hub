/**
 * Directory Operations Module
 * Handles directory copying and operations
 */

// =============================================================================

/**
 * Copy entire project/directory content to clipboard
 */
async function copyProjectToClipboard() {
  console.log("copyProjectToClipboard() called");
  const btn = document.getElementById("copy-project-btn");
  if (!btn) return;

  const originalText = btn.innerHTML;
  btn.innerHTML = "⏳ Loading...";
  (btn as HTMLButtonElement).disabled = true;

  const pathParts = window.location.pathname.split("/").filter((x) => x);
  if (pathParts.length < 2) return;

  const username = pathParts[0];
  const slug = pathParts[1];
  const subpath = pathParts.slice(2).join("/");

  try {
    console.log("Fetching concatenated content...");
    const response = await fetch(
      `/${username}/${slug}/api/concatenate/${subpath}`,
    );
    const data = await response.json();
    console.log("API response:", data);

    if (data.success) {
      await navigator.clipboard.writeText(data.content);
      btn.innerHTML = `✓ Copied ${data.file_count} files!`;
      setTimeout(() => {
        btn.innerHTML = originalText;
        (btn as HTMLButtonElement).disabled = false;
      }, 3000);
    } else {
      alert("Error: " + data.error);
      btn.innerHTML = originalText;
      (btn as HTMLButtonElement).disabled = false;
    }
  } catch (err) {
    alert("Failed to copy: " + err);
    btn.innerHTML = originalText;
    (btn as HTMLButtonElement).disabled = false;
  }
}

/**
 * Download project/directory content as file
 */
async function downloadProjectAsFile() {
  const btn = (event as Event).target as HTMLElement;
  const originalText = btn.innerHTML;
  btn.innerHTML = "⏳ Preparing download...";

  const pathParts = window.location.pathname
    .split("/")
    .filter((x: string) => x);
  if (pathParts.length < 2) return;

  const username = pathParts[0];
  const slug = pathParts[1];
  const subpath = pathParts.slice(2).join("/");

  try {
    const response = await fetch(
      `/${username}/${slug}/api/concatenate/${subpath}`,
    );
    const data = await response.json();

    if (data.success) {
      const blob = new Blob([data.content], { type: "text/plain" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;

      const dirName =
        subpath
          .split("/")
          .filter((x) => x)
          .pop() || slug;
      a.download = `${dirName}_all_files.txt`;

      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      btn.innerHTML = `✓ Downloaded ${data.file_count} files!`;
      setTimeout(() => {
        btn.innerHTML = originalText;
      }, 3000);
    } else {
      alert("Error: " + data.error);
      btn.innerHTML = originalText;
    }
  } catch (err) {
    alert("Failed to download: " + err);
    btn.innerHTML = originalText;
  }
}

/**
 * Toggle branch dropdown
 */
export function toggleBranchDropdown(event?: Event) {
  if (event) event.stopPropagation();
  const dropdown = document.getElementById("branchDropdown");
  if (dropdown) {
    dropdown.classList.toggle("show");
  }
}

/**
 * Switch to different Git branch
 */
async function switchBranch(branch: string) {
  console.log("Switching to branch:", branch);

  const pathParts = window.location.pathname
    .split("/")
    .filter((x: string) => x);
  if (pathParts.length < 2) return;

  const username = pathParts[0];
  const slug = pathParts[1];

  try {
    const response = await fetch(`/${username}/${slug}/api/switch-branch/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ branch: branch }),
    });

    const data = await response.json();

    if (data.success) {
      window.location.reload();
    } else {
      alert("Failed to switch branch: " + data.error);
    }
  } catch (error) {
    console.error("Error switching branch:", error);
    const errorMessage =
      error instanceof Error ? error.message : "Unknown error";
    alert("Failed to switch branch: " + errorMessage);
  }
}

/**
 * Toggle dropdown menus
 */
export function toggleAddFileDropdown(): void {
  const dropdown = document.getElementById("add-file-dropdown");
  if (dropdown) {
    const isVisible = (dropdown as HTMLElement).style.display === "block";
    closeAllDropdowns();
    (dropdown as HTMLElement).style.display = isVisible ? "none" : "block";
  }
}

export function toggleCopyDropdown(): void {
  const dropdown = document.getElementById("copy-dropdown");
  if (dropdown) {
    const isVisible = (dropdown as HTMLElement).style.display === "block";
    closeAllDropdowns();
    (dropdown as HTMLElement).style.display = isVisible ? "none" : "block";
  }
}

export function toggleCodeDropdown(): void {
  const dropdown = document.getElementById("code-dropdown");
  if (dropdown) {
    const isVisible = (dropdown as HTMLElement).style.display === "block";
    closeAllDropdowns();
    (dropdown as HTMLElement).style.display = isVisible ? "none" : "block";
  }
}

export function toggleMoreDropdown(): void {
  const dropdown = document.getElementById("more-dropdown");
  if (dropdown) {
    const isVisible = (dropdown as HTMLElement).style.display === "block";
    closeAllDropdowns();
    (dropdown as HTMLElement).style.display = isVisible ? "none" : "block";
  }
}

export function closeAllDropdowns(): void {
  document
    .querySelectorAll(".dropdown-menu, .file-browser-toolbar .dropdown-menu")
    .forEach((dropdown) => {
      (dropdown as HTMLElement).style.display = "none";
    });
}

