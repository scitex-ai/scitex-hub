/**
 * Manuscript Status
 * Asks the server what exists, so loaders never use a 404 as an existence probe.
 */

export interface ManuscriptStatus {
  exists: boolean;
  has_pdf: boolean;
}

export type ManuscriptStatusFetcher = (
  projectId: number | string,
  pdfFilename?: string,
) => Promise<ManuscriptStatus>;

export function manuscriptStatusUrl(
  projectId: number | string,
  pdfFilename?: string,
): string {
  const query = pdfFilename ? `?pdf=${encodeURIComponent(pdfFilename)}` : "";
  return `/apps/writer/api/project/${projectId}/manuscript-status/${query}`;
}

export const fetchManuscriptStatus: ManuscriptStatusFetcher = async (
  projectId,
  pdfFilename,
) => {
  const response = await fetch(manuscriptStatusUrl(projectId, pdfFilename));
  if (!response.ok) {
    throw new Error(`Manuscript status unavailable: ${response.status}`);
  }
  const data = await response.json();
  return { exists: Boolean(data.exists), has_pdf: Boolean(data.has_pdf) };
};
