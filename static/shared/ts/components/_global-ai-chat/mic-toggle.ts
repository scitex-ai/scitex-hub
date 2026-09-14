/** Chat mic button: browser dictation first, server STT only where recording works. */

import { getCsrfToken } from "../../utils/csrf";
import {
  detectVoiceInputEnv,
  toggleVoiceInput,
  voiceInputMessage,
} from "../voice-input";
import type { VoiceRecorder } from "./recorder";

export function toggleChatMic(
  recorder: VoiceRecorder | null,
  inputEl: HTMLTextAreaElement | null,
  micBtn: HTMLButtonElement | null,
  getModel: () => string,
): void {
  if (recorder?.isRecording) {
    recorder.stop();
    return;
  }
  if (!inputEl || !micBtn) return;
  const env = detectVoiceInputEnv();
  const canRecord =
    typeof MediaRecorder !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia;
  if (env.Recognition || env.isIosPwa || !canRecord || !recorder) {
    toggleVoiceInput(inputEl, micBtn, env);
    return;
  }
  void recorder.start(
    () => getCsrfToken(),
    (text) => {
      const cur = inputEl.value.trim();
      inputEl.value = cur ? `${cur} ${text}` : text;
      inputEl.dispatchEvent(new Event("input"));
      inputEl.focus();
    },
    getModel,
    () => env.toast(voiceInputMessage("denied", env.lang)),
  );
}
