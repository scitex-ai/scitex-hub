/**
 * ExportManagerDownload - Bundle download helpers for ExportManager
 *
 * Extracted from ExportManager.ts for file-size compliance.
 * Contains download methods for figz and pltz bundles.
 */

/**
 * Get CSRF token from cookie
 */
export function getCSRFToken(): string {
  const cookies = document.cookie.split(";");
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split("=");
    if (name === "csrftoken") {
      return value;
    }
  }
  return "";
}

/**
 * Trigger a browser download via a temporary link element
 */
export function triggerDownloadLink(url: string, filename: string = ""): void {
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

/**
 * Download the current figz bundle as .figz ZIP file via GET endpoint
 */
export function downloadFigzBundle(
  currentFigzPath: string | undefined,
  statusCallback?: (message: string) => void,
): void {
  if (!currentFigzPath) {
    console.warn("[ExportManager] No figz bundle loaded");
    if (statusCallback) {
      statusCallback("No figure loaded to download");
    }
    return;
  }

  const downloadUrl = `/vis/api/bundles/figz/download/?path=${encodeURIComponent(currentFigzPath)}`;
  triggerDownloadLink(downloadUrl, "");

  if (statusCallback) {
    statusCallback("Downloading figz bundle...");
  }
  console.log("[ExportManager] Downloading figz bundle:", currentFigzPath);
}

/**
 * Download the current figz bundle (zipped format) as .figz ZIP file
 */
export function downloadFigzBundleZip(
  currentFigzPath: string | undefined,
  statusCallback?: (message: string) => void,
): void {
  if (!currentFigzPath) {
    console.warn("[ExportManager] No figz bundle loaded");
    if (statusCallback) {
      statusCallback("No figure loaded to download");
    }
    return;
  }

  const downloadUrl = `/vis/api/bundles/figz/download/?path=${encodeURIComponent(currentFigzPath)}`;
  triggerDownloadLink(downloadUrl, "");

  if (statusCallback) {
    statusCallback("Downloading figz bundle...");
  }
  console.log(
    "[ExportManager] Downloading figz bundle (zipped):",
    currentFigzPath,
  );
}

/**
 * Download a pltz bundle as .pltz ZIP file
 */
export function downloadPltzBundle(
  pltzPath: string,
  statusCallback?: (message: string) => void,
): void {
  if (!pltzPath) {
    console.warn("[ExportManager] No pltz path provided");
    if (statusCallback) {
      statusCallback("No panel to download");
    }
    return;
  }

  const downloadUrl = `/vis/api/bundles/pltz/download/?path=${encodeURIComponent(pltzPath)}`;
  triggerDownloadLink(downloadUrl, "");

  if (statusCallback) {
    statusCallback("Downloading pltz bundle...");
  }
  console.log("[ExportManager] Downloading pltz bundle:", pltzPath);
}
