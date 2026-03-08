/**
 * VoiceRecorder — MediaRecorder + Web Audio volume visualizer for the AI panel.
 * Uploads recorded audio to /apps/llm/api/stt/ and returns the transcribed text.
 */

import { API_URLS } from "../../utils/api-urls";

export class VoiceRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private analyser: AnalyserNode | null = null;
  private animFrame: number | null = null;
  private stream: MediaStream | null = null;
  private _isRecording = false;

  constructor(
    private readonly volBars: HTMLElement[],
    private readonly micBtn: HTMLButtonElement | null,
  ) {}

  get isRecording(): boolean {
    return this._isRecording;
  }

  async start(
    getCsrf: () => string,
    onTranscript: (text: string) => void,
    getModel?: () => string,
  ): Promise<void> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      console.error("[STT] Microphone access denied:", err);
      return;
    }

    this.audioChunks = [];
    this.mediaRecorder = new MediaRecorder(this.stream);

    this.mediaRecorder.addEventListener("dataavailable", (e: BlobEvent) => {
      if (e.data.size > 0) this.audioChunks.push(e.data);
    });

    this.mediaRecorder.addEventListener("stop", () => {
      void this._transcribe(getCsrf(), onTranscript, getModel?.());
    });

    this.mediaRecorder.start();
    this._isRecording = true;
    this.micBtn?.classList.add("recording");
    this._startVisualizer();
  }

  stop(): void {
    this.mediaRecorder?.stop();
    this._isRecording = false;
    this.micBtn?.classList.remove("recording");
    this.micBtn?.classList.add("transcribing");
    this._stopVisualizer();
  }

  private _startVisualizer(): void {
    if (!this.stream) return;
    const ctx = new AudioContext();
    const source = ctx.createMediaStreamSource(this.stream);
    this.analyser = ctx.createAnalyser();
    this.analyser.fftSize = 64;
    source.connect(this.analyser);

    const data = new Uint8Array(this.analyser.frequencyBinCount);
    const bars = this.volBars;
    const n = bars.length;

    const tick = (): void => {
      this.analyser!.getByteFrequencyData(data);
      const step = Math.floor(data.length / n);
      for (let i = 0; i < n; i++) {
        const avg = data[i * step] / 255;
        const scale = Math.max(0.1, avg);
        (bars[i] as HTMLElement).style.transform = `scaleY(${scale})`;
      }
      this.animFrame = requestAnimationFrame(tick);
    };

    this.animFrame = requestAnimationFrame(tick);
    bars.forEach((b) => b.removeAttribute("hidden"));
  }

  private _stopVisualizer(): void {
    if (this.animFrame !== null) {
      cancelAnimationFrame(this.animFrame);
      this.animFrame = null;
    }
    this.volBars.forEach((b) => {
      (b as HTMLElement).style.transform = "scaleY(0.1)";
      b.setAttribute("hidden", "");
    });
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.analyser = null;
  }

  private async _transcribe(
    csrf: string,
    onTranscript: (text: string) => void,
    model?: string,
  ): Promise<void> {
    const blob = new Blob(this.audioChunks, { type: "audio/webm" });
    const form = new FormData();
    form.append("audio", blob, "recording.webm");
    if (model) form.append("model", model);
    try {
      const resp = await fetch(API_URLS.llm.stt, {
        method: "POST",
        headers: { "X-CSRFToken": csrf },
        body: form,
      });
      const data = (await resp.json()) as {
        text?: string;
        error?: string;
        model?: string;
      };
      if (data.error) {
        console.error("[STT] Server error:", data.error);
      } else if (data.text) {
        onTranscript(data.text);
      }
    } catch (err) {
      console.error("[STT] Request failed:", err);
    } finally {
      this.micBtn?.classList.remove("transcribing");
    }
  }
}
