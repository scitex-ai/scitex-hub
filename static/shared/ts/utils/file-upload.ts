/**
 * Shared file upload utility.
 * Uploads files via FormData to /apps/llm/api/upload/ and returns server paths.
 */

import { getCsrfToken } from "./csrf";

export async function uploadFiles(files: FileList): Promise<string[]> {
  const form = new FormData();
  for (let i = 0; i < files.length; i++) form.append("files", files[i]);

  const resp = await fetch("/apps/llm/api/upload/", {
    method: "POST",
    headers: { "X-CSRFToken": getCsrfToken() },
    body: form,
  });
  if (!resp.ok) throw new Error(`Upload failed: ${resp.status}`);
  const data = (await resp.json()) as { paths: string[] };
  return data.paths;
}
