/**
 * File Drop Handler for AI Chat
 *
 * Handles drag-and-drop of files onto the AI chat panel:
 * - Internal file tree drops: references existing server paths
 * - External OS file drops: uploads to user's downloads directory
 */

import { uploadFiles } from "../../utils/file-upload";

function notifyFilesAttached(
  paths: string[],
  inputEl: HTMLTextAreaElement,
): void {
  const label =
    paths.length === 1
      ? `Uploaded file: ${paths[0]}`
      : `Uploaded files:\n${paths.map((p) => `  ${p}`).join("\n")}`;
  const existing = inputEl.value.trim();
  inputEl.value = existing ? `${existing}\n${label}` : label;
  inputEl.focus();
}

/**
 * Initialize file drop handlers on the given drop zone.
 * - Internal drops (file tree): inserts server paths into the input
 * - External drops (OS files): uploads to server, then inserts paths
 */
export function initFileDrop(
  dropZone: HTMLElement,
  inputEl: HTMLTextAreaElement,
): void {
  // Prevent browser default navigation on drop anywhere in the document
  document.addEventListener("dragover", (e) => e.preventDefault());
  document.addEventListener("drop", (e) => e.preventDefault());

  const wrap = inputEl.closest(".scitex-ai-input-wrap") ?? inputEl;

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
    wrap.classList.add("drop-target");
  });

  dropZone.addEventListener("dragleave", (e) => {
    if (!dropZone.contains(e.relatedTarget as Node)) {
      wrap.classList.remove("drop-target");
    }
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation();
    wrap.classList.remove("drop-target");

    const dt = e.dataTransfer;
    if (!dt) return;

    // External OS file drops (binary upload)
    if (dt.files && dt.files.length > 0) {
      console.log("[AI Chat] OS files dropped:", dt.files.length);
      void (async () => {
        try {
          const paths = await uploadFiles(dt.files);
          notifyFilesAttached(paths, inputEl);
        } catch (err) {
          console.error("[AI Chat] File upload error:", err);
        }
      })();
      return;
    }

    // Internal file tree drops (paths already on server)
    const raw = dt.getData("text/plain") ?? "";
    const paths = raw.split(";").filter(Boolean);
    if (paths.length > 0) {
      console.log("[AI Chat] File tree paths dropped:", paths);
      notifyFilesAttached(paths, inputEl);
    }
  });
}
