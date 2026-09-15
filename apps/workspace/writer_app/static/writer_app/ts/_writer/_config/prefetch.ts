/**
 * One-shot GET prefetch: start a request while the editor boots, let the
 * first real caller of the same URL take it. Unclaimed entries expire.
 */
const MAX_AGE_MS = 10000;
const entries = new Map<string, { at: number; response: Promise<Response> }>();

export function prefetch(url: string): void {
  if (entries.has(url)) return;
  const response = fetch(url);
  response.catch(() => entries.delete(url));
  entries.set(url, { at: Date.now(), response });
}

export function takePrefetched(url: string): Promise<Response> | null {
  const entry = entries.get(url);
  if (!entry) return null;
  entries.delete(url);
  return Date.now() - entry.at < MAX_AGE_MS ? entry.response : null;
}

export function sectionContentUrl(
  projectId: number | string,
  sectionId: string,
): string | null {
  const [docType, sectionName] = sectionId.split("/");
  if (!docType || !sectionName) return null;
  return `/apps/writer/api/project/${projectId}/section/${sectionName}/?doc_type=${docType}`;
}
