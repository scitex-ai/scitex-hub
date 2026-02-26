/**
 * Webcam Capture — live camera feed with snapshot for AI chat.
 *
 * Opens a modal overlay with getUserMedia video stream.
 * User clicks "Capture" to take a photo, which is added as an image attachment.
 * Falls back to file picker if camera access is denied.
 */

import type { ImageInputManager } from "./image-input";

export class WebcamCapture {
  private overlay: HTMLElement | null = null;
  private video: HTMLVideoElement | null = null;
  private stream: MediaStream | null = null;
  private imageInput: ImageInputManager;
  private fileInput: HTMLInputElement;

  constructor(imageInput: ImageInputManager, fileInput: HTMLInputElement) {
    this.imageInput = imageInput;
    this.fileInput = fileInput;
  }

  async open(): Promise<void> {
    if (this.overlay) return;

    // Try webcam first; fall back to file picker on failure
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 } },
        audio: false,
      });
    } catch {
      // Camera unavailable or denied — fall back to file picker
      this.fileInput.click();
      return;
    }

    this.overlay = this.buildUI();
    document.body.appendChild(this.overlay);
    this.video!.srcObject = this.stream;
  }

  close(): void {
    this.stopStream();
    this.overlay?.remove();
    this.overlay = null;
    this.video = null;
  }

  /* ── UI ─────────────────────────────────────────────────────── */

  private buildUI(): HTMLElement {
    const overlay = document.createElement("div");
    overlay.className = "scitex-webcam-overlay";

    const panel = document.createElement("div");
    panel.className = "scitex-webcam-panel";
    overlay.appendChild(panel);

    // Video element
    this.video = document.createElement("video");
    this.video.className = "scitex-webcam-video";
    this.video.autoplay = true;
    this.video.playsInline = true;
    this.video.muted = true;
    panel.appendChild(this.video);

    // Actions
    const actions = document.createElement("div");
    actions.className = "scitex-webcam-actions";

    const cancelBtn = document.createElement("button");
    cancelBtn.className = "scitex-sketch-btn";
    cancelBtn.textContent = "Cancel";
    cancelBtn.addEventListener("click", () => this.close());

    const captureBtn = document.createElement("button");
    captureBtn.className = "scitex-webcam-capture-btn";
    captureBtn.title = "Take photo";
    captureBtn.innerHTML = '<i class="fas fa-circle"></i>';
    captureBtn.addEventListener("click", () => this.capture());

    const switchBtn = document.createElement("button");
    switchBtn.className = "scitex-sketch-btn";
    switchBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Flip';
    switchBtn.addEventListener("click", () => this.switchCamera());

    actions.append(cancelBtn, captureBtn, switchBtn);
    panel.appendChild(actions);

    // Close on overlay click
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) this.close();
    });

    // Esc to close
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        this.close();
        document.removeEventListener("keydown", onKey);
      }
    };
    document.addEventListener("keydown", onKey);

    return overlay;
  }

  /* ── Actions ────────────────────────────────────────────────── */

  private capture(): void {
    if (!this.video) return;
    const canvas = document.createElement("canvas");
    canvas.width = this.video.videoWidth || 640;
    canvas.height = this.video.videoHeight || 480;
    const ctx = canvas.getContext("2d")!;
    ctx.drawImage(this.video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
    this.imageInput.addImageFromDataUrl(dataUrl, "image/jpeg");
    this.close();
  }

  private async switchCamera(): Promise<void> {
    if (!this.stream || !this.video) return;
    const currentTrack = this.stream.getVideoTracks()[0];
    const currentFacing =
      currentTrack.getSettings().facingMode || "environment";
    const newFacing = currentFacing === "environment" ? "user" : "environment";

    this.stopStream();
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: newFacing, width: { ideal: 1280 } },
        audio: false,
      });
      this.video.srcObject = this.stream;
    } catch {
      /* only one camera available — ignore */
    }
  }

  private stopStream(): void {
    if (this.stream) {
      for (const track of this.stream.getTracks()) track.stop();
      this.stream = null;
    }
  }
}
