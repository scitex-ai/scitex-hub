/**
 * File loader for the shared Workspace Viewer component.
 * Abstracts content fetching with strategy selection based on file type.
 * Text-like files are fetched as JSON; binary media files use blob URLs.
 */

import { detectFileType, type FileType } from "./types.js";

/** Result returned by loadFileContent */
export interface FileLoadResult {
  content: string;
  mimeType: string;
  isBase64: boolean;
  blobUrl?: string;
}

/** File types that are fetched as raw binary and rendered via blob URL */
const BINARY_MEDIA_TYPES = new Set<FileType>([
  "image",
  "pdf",
  "audio",
  "video",
]);

/** Default API endpoint for file content */
const DEFAULT_API_ENDPOINT = "/api/workspace/file-content/";

/** Configurable API endpoint — can be overridden for different apps */
let apiEndpoint = DEFAULT_API_ENDPOINT;

/**
 * Override the API endpoint used by this loader.
 * Call once at app initialization if the endpoint differs from the default.
 */
export function configureApiEndpoint(endpoint: string): void {
  apiEndpoint = endpoint;
}

/**
 * Build the URL for a file content request.
 *
 * @param filePath  - Path to the file within the project
 * @param projectId - Project identifier
 * @param raw       - When true, returns raw binary response (default: false)
 */
export function getFileUrl(
  filePath: string,
  projectId: string,
  raw = false,
): string {
  const params = new URLSearchParams({ project_id: projectId });
  if (raw) {
    params.set("raw", "true");
  }
  return `${apiEndpoint}${encodeURIComponent(filePath)}?${params.toString()}`;
}

/**
 * Load file content, choosing text-JSON or raw-binary strategy based on type.
 *
 * For text, csv, and mermaid files:
 *   - Fetches JSON response with a `content` field.
 *
 * For image, pdf, audio, and video files:
 *   - Fetches raw binary and creates an object URL (blob URL).
 *   - Caller is responsible for revoking the blob URL when done.
 *
 * @throws Error when the HTTP request fails or the server returns an error.
 */
export async function loadFileContent(
  filePath: string,
  projectId: string,
): Promise<FileLoadResult> {
  const fileType = detectFileType(filePath);

  if (BINARY_MEDIA_TYPES.has(fileType)) {
    return loadBinaryMedia(filePath, projectId, fileType);
  }

  return loadTextContent(filePath, projectId);
}

/**
 * Revoke a previously created blob URL to free browser memory.
 */
export function revokeFileUrl(blobUrl: string): void {
  URL.revokeObjectURL(blobUrl);
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

async function loadTextContent(
  filePath: string,
  projectId: string,
): Promise<FileLoadResult> {
  const url = getFileUrl(filePath, projectId, false);
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(
      `Failed to load file "${filePath}": HTTP ${response.status}`,
    );
  }

  const json = await response.json();
  const content: string = json.content ?? "";
  const mimeType: string = response.headers.get("content-type") ?? "text/plain";

  return { content, mimeType, isBase64: false };
}

async function loadBinaryMedia(
  filePath: string,
  projectId: string,
  fileType: FileType,
): Promise<FileLoadResult> {
  const url = getFileUrl(filePath, projectId, true);
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(
      `Failed to load file "${filePath}": HTTP ${response.status}`,
    );
  }

  const blob = await response.blob();
  const mimeType = blob.type || inferMimeType(filePath, fileType);
  const typedBlob =
    mimeType !== blob.type ? blob.slice(0, blob.size, mimeType) : blob;
  const blobUrl = URL.createObjectURL(typedBlob);

  return { content: "", mimeType, isBase64: false, blobUrl };
}

/** Fallback MIME type inference when the server omits Content-Type */
function inferMimeType(filePath: string, fileType: FileType): string {
  const ext = filePath.substring(filePath.lastIndexOf(".")).toLowerCase();

  const mimeMap: { [key: string]: string } = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
    ".ico": "image/x-icon",
    ".pdf": "application/pdf",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".wma": "audio/x-ms-wma",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
    ".ogv": "video/ogg",
  };

  if (mimeMap[ext]) return mimeMap[ext];

  // Broad fallback by category
  if (fileType === "image") return "image/png";
  if (fileType === "pdf") return "application/pdf";
  if (fileType === "audio") return "audio/mpeg";
  if (fileType === "video") return "video/mp4";
  return "application/octet-stream";
}
