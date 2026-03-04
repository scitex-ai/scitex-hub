/**
 * Shared upload utilities for terminal and file tree.
 * Provides CSRF token extraction and file upload to scitex/downloads/.
 */

/** Get CSRF token from cookie or hidden input. */
export function getCsrf(): string {
  return (
    document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
      ?.value ??
    (document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "")
  );
}

/** Upload files to project's scitex/downloads/ directory. */
export async function uploadFiles(
  files: File[],
  projectId: number,
): Promise<string[]> {
  const form = new FormData();
  form.append("project_id", String(projectId));
  for (const file of files) form.append("files", file);

  const resp = await fetch("/console/api/paste-upload/", {
    method: "POST",
    headers: { "X-CSRFToken": getCsrf() },
    body: form,
  });

  if (!resp.ok) throw new Error(`Upload failed: ${resp.status}`);
  const data = await resp.json();
  return data.paths as string[];
}
