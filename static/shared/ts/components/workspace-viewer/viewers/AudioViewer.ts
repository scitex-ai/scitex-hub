/**
 * AudioViewer - Simple HTML5 audio player for audio files.
 */

import type { Viewer } from "../types";
import { getFileUrl } from "../_file-loader";

export class AudioViewer implements Viewer {
  private audio: HTMLAudioElement | null = null;

  async render(
    container: HTMLElement,
    filePath: string,
    projectId: string,
  ): Promise<void> {
    const rawUrl = getFileUrl(filePath, projectId, true);
    const fileName = filePath.split("/").pop() || filePath;
    const ext = fileName.includes(".")
      ? fileName.split(".").pop()?.toUpperCase()
      : "Audio";

    container.innerHTML = "";

    const wrapper = document.createElement("div");
    wrapper.style.cssText =
      "display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; gap:12px; padding:20px;";

    const nameEl = document.createElement("div");
    nameEl.style.cssText =
      "font-size:0.9em; color:#aaa; text-align:center; word-break:break-all;";
    nameEl.title = filePath;
    nameEl.textContent = fileName;

    const formatEl = document.createElement("div");
    formatEl.style.cssText =
      "font-size:0.75em; color:#666; text-transform:uppercase; letter-spacing:1px;";
    formatEl.textContent = ext || "Audio";

    this.audio = document.createElement("audio");
    this.audio.controls = true;
    this.audio.src = rawUrl;
    this.audio.style.cssText = "width:100%; max-width:480px;";

    this.audio.onerror = () => {
      const err = document.createElement("div");
      err.style.cssText = "color:#e55; font-size:0.9em; text-align:center;";
      err.textContent = `Failed to load audio: ${fileName}`;
      wrapper.replaceChild(err, this.audio!);
      this.audio = null;
    };

    wrapper.appendChild(nameEl);
    wrapper.appendChild(formatEl);
    wrapper.appendChild(this.audio);
    container.appendChild(wrapper);
  }

  destroy(): void {
    if (this.audio) {
      this.audio.pause();
      this.audio.src = "";
      this.audio = null;
    }
  }
}
