/**
 * Audio settings: auto-speak mode selector for the AI panel.
 * Modes: off, server (server-side TTS), browser (Web Speech API).
 */

const AUDIO_MODE_KEY = "scitex_audio_mode";

export type AudioMode = "off" | "server" | "browser";

export function getAudioMode(): AudioMode {
  return (localStorage.getItem(AUDIO_MODE_KEY) as AudioMode) || "off";
}

export function initAudioModeSelector(
  select: HTMLSelectElement,
  speakBtn: HTMLButtonElement | null,
): void {
  const saved = getAudioMode();
  select.value = saved;
  updateSpeakBtn(speakBtn, saved);

  select.addEventListener("change", () => {
    const mode = select.value as AudioMode;
    localStorage.setItem(AUDIO_MODE_KEY, mode);
    updateSpeakBtn(speakBtn, mode);
  });
}

function updateSpeakBtn(btn: HTMLButtonElement | null, mode: AudioMode): void {
  if (!btn) return;
  btn.classList.toggle("active", mode !== "off");
  btn.title = mode === "off" ? "Auto-speak: off" : `Auto-speak: ${mode}`;
}
