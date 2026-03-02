/**
 * Image Input Manager for AI Chat
 *
 * Manages image attachments: file picker, clipboard paste, thumbnails.
 * Exports base64 payloads for multimodal LLM messages.
 */

interface Attachment {
  file: File;
  dataUrl: string;
  mime: string;
  thumbEl: HTMLElement;
}

const MAX_IMAGES = 4;
const MAX_SIZE_BYTES = 20 * 1024 * 1024; // 20 MB

export class ImageInputManager {
  private previewEl: HTMLElement;
  private fileInput: HTMLInputElement;
  private attachments: Attachment[] = [];

  constructor(previewEl: HTMLElement, fileInput: HTMLInputElement) {
    this.previewEl = previewEl;
    this.fileInput = fileInput;
    this.fileInput.addEventListener("change", () => this.onFilesSelected());
  }

  /** Bind clipboard paste on a textarea */
  bindPaste(textarea: HTMLTextAreaElement): void {
    textarea.addEventListener("paste", (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of Array.from(items)) {
        if (item.type.startsWith("image/")) {
          e.preventDefault();
          const file = item.getAsFile();
          if (file) this.addFile(file);
        }
      }
    });
  }

  /** Add image from a data URL (used by sketch canvas) */
  addImageFromDataUrl(dataUrl: string, mime: string): void {
    if (this.attachments.length >= MAX_IMAGES) return;
    // Convert data URL to File for consistency
    const byteStr = atob(dataUrl.split(",")[1]);
    const ab = new ArrayBuffer(byteStr.length);
    const ia = new Uint8Array(ab);
    for (let i = 0; i < byteStr.length; i++) ia[i] = byteStr.charCodeAt(i);
    const file = new File([ab], "sketch.png", { type: mime });
    this.addAttachment(file, dataUrl, mime);
  }

  hasAttachments(): boolean {
    return this.attachments.length > 0;
  }

  async getAttachmentsAsBase64(): Promise<{ mime: string; base64: string }[]> {
    return this.attachments.map((a) => ({
      mime: a.mime,
      base64: a.dataUrl.split(",")[1],
    }));
  }

  clearAttachments(): void {
    this.attachments = [];
    this.previewEl.innerHTML = "";
  }

  /** Render small inline thumbnails inside a user message bubble */
  renderInlineThumbsInto(container: HTMLElement): void {
    if (this.attachments.length === 0) return;
    const strip = document.createElement("div");
    strip.className = "scitex-ai-msg-thumbs";
    for (const a of this.attachments) {
      const img = document.createElement("img");
      img.src = a.dataUrl;
      img.className = "scitex-ai-msg-thumb";
      strip.appendChild(img);
    }
    container.appendChild(strip);
  }

  /* ── Private ────────────────────────────────────────────────── */

  private onFilesSelected(): void {
    const files = this.fileInput.files;
    if (!files) return;
    for (const file of Array.from(files)) this.addFile(file);
    this.fileInput.value = "";
  }

  private addFile(file: File): void {
    if (this.attachments.length >= MAX_IMAGES) return;
    if (file.size > MAX_SIZE_BYTES) return;
    if (!file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      this.addAttachment(file, dataUrl, file.type);
    };
    reader.readAsDataURL(file);
  }

  private addAttachment(file: File, dataUrl: string, mime: string): void {
    const thumb = document.createElement("div");
    thumb.className = "scitex-ai-image-thumb";

    const img = document.createElement("img");
    img.src = dataUrl;
    thumb.appendChild(img);

    const removeBtn = document.createElement("button");
    removeBtn.className = "scitex-ai-image-thumb-remove";
    removeBtn.innerHTML = "&times;";
    removeBtn.addEventListener("click", () => this.removeAttachment(att));
    thumb.appendChild(removeBtn);

    this.previewEl.appendChild(thumb);
    const att: Attachment = { file, dataUrl, mime, thumbEl: thumb };
    this.attachments.push(att);
  }

  private removeAttachment(att: Attachment): void {
    const idx = this.attachments.indexOf(att);
    if (idx >= 0) this.attachments.splice(idx, 1);
    att.thumbEl.remove();
  }
}
