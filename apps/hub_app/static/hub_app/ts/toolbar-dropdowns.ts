/**
 * Hub Toolbar Dropdown Handlers
 * Manages dropdown menus in the project browse toolbar (hub_tabs.html).
 * Exposes toggle functions to window for onclick attributes.
 */

function closeAllToolbarDropdowns(): void {
  const ids = [
    "branch-dropdown",
    "add-file-dropdown",
    "code-dropdown",
    "copy-dropdown",
    "import-export-dropdown",
  ];
  ids.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.style.display = "none";
  });
}

function toggleToolbarDropdown(dropdownId: string): void {
  const dropdown = document.getElementById(dropdownId);
  if (!dropdown) return;
  const isVisible = dropdown.style.display === "block";
  closeAllToolbarDropdowns();
  dropdown.style.display = isVisible ? "none" : "block";
}

// --- Expose toggle functions to window for onclick handlers ---

(window as any).toggleAddFileDropdown = () =>
  toggleToolbarDropdown("add-file-dropdown");
(window as any).toggleImportExportDropdown = () =>
  toggleToolbarDropdown("import-export-dropdown");
(window as any).toggleCopyDropdown = () =>
  toggleToolbarDropdown("copy-dropdown");
(window as any).toggleBranchDropdown = () =>
  toggleToolbarDropdown("branch-dropdown");
(window as any).toggleCodeDropdown = () =>
  toggleToolbarDropdown("code-dropdown");

(window as any).showImportModal = (source: string) => {
  closeAllToolbarDropdowns();
  if (["zotero", "connected-papers", "prism"].includes(source)) {
    window.location.href = "/scholar/#library";
    return;
  }
  alert(`Import from ${source} — coming soon.`);
};

(window as any).handleExport = (target: string) => {
  closeAllToolbarDropdowns();
  if (["zotero", "connected-papers", "prism"].includes(target)) {
    window.location.href = "/scholar/#library";
    return;
  }
  alert(`Export to ${target} — coming soon.`);
};

(window as any).copyProjectToClipboard = async () => {
  const projData = (window as any).SCITEX_PROJECT_DATA;
  if (!projData) return;
  const btn = document.getElementById("copy-project-btn");
  if (!btn) return;
  const originalHTML = btn.innerHTML;
  btn.textContent = "Copying...";
  (btn as HTMLButtonElement).disabled = true;
  try {
    const resp = await fetch(
      `/${projData.owner}/${projData.slug}/api/concatenate/`,
    );
    const data = await resp.json();
    if (data.success) {
      await navigator.clipboard.writeText(data.content);
      btn.textContent = `Copied ${data.file_count} files!`;
      setTimeout(() => {
        btn.innerHTML = originalHTML;
        (btn as HTMLButtonElement).disabled = false;
      }, 3000);
    } else {
      btn.innerHTML = originalHTML;
      (btn as HTMLButtonElement).disabled = false;
    }
  } catch {
    btn.innerHTML = originalHTML;
    (btn as HTMLButtonElement).disabled = false;
  }
};

(window as any).downloadProjectAsFile = async () => {
  const projData = (window as any).SCITEX_PROJECT_DATA;
  if (!projData) return;
  try {
    const resp = await fetch(
      `/${projData.owner}/${projData.slug}/api/concatenate/`,
    );
    const data = await resp.json();
    if (data.success) {
      const blob = new Blob([data.content], { type: "text/plain" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${projData.slug}_all_files.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    }
  } catch (err) {
    alert("Failed to download: " + err);
  }
};

// Close dropdowns on outside click
document.addEventListener("click", (e: Event) => {
  const target = e.target as HTMLElement;
  if (!target.closest(".btn-group") && !target.closest(".copy-btn-group")) {
    closeAllToolbarDropdowns();
  }
});
