/**
 * Project Concatenation Handlers
 * Copy all project files to clipboard or download as single file
 */

export async function copyProjectToClipboard(event: Event): Promise<void> {
  const projectData = (window as any).SCITEX_PROJECT_DATA;
  if (!projectData) return;

  const btn = event.currentTarget as HTMLButtonElement;
  const originalText = btn.innerHTML;
  btn.innerHTML = "⏳ Loading...";
  btn.disabled = true;

  try {
    const response = await fetch(
      `/${projectData.owner}/${projectData.slug}/api/concatenate/`,
    );
    const data = await response.json();

    if (data.success) {
      await navigator.clipboard.writeText(data.content);
      const checkIcon =
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" class="octicon octicon-16" style="vertical-align: text-bottom; margin-right: 4px;"><path fill="currentColor" d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path></svg>';
      btn.innerHTML = `${checkIcon} Copied ${data.file_count} files!`;
      setTimeout(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
      }, 3000);
    } else {
      alert("Error: " + data.error);
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  } catch (err) {
    alert("Failed to copy: " + err);
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

export async function downloadProjectAsFile(event: Event): Promise<void> {
  const projectData = (window as any).SCITEX_PROJECT_DATA;
  if (!projectData) return;

  const btn = event.currentTarget as HTMLButtonElement;
  const originalText = btn.innerHTML;
  btn.innerHTML = "⏳ Preparing download...";
  btn.disabled = true;

  try {
    const response = await fetch(
      `/${projectData.owner}/${projectData.slug}/api/concatenate/`,
    );
    const data = await response.json();

    if (data.success) {
      // Create a blob and download it
      const blob = new Blob([data.content], { type: "text/plain" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${projectData.slug}_all_files.txt`;

      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      const checkIcon =
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" class="octicon octicon-16" style="vertical-align: text-bottom; margin-right: 4px;"><path fill="currentColor" d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path></svg>';
      btn.innerHTML = `${checkIcon} Downloaded ${data.file_count} files!`;
      setTimeout(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
      }, 3000);
    } else {
      alert("Error: " + data.error);
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  } catch (err) {
    alert("Failed to download: " + err);
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}
