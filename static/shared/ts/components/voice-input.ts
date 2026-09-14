/**
 * Voice input for chat textareas via the browser's SpeechRecognition.
 * Falls back to a toast pointing at keyboard dictation — never silent.
 */

import { showToast } from "../utils/ui";

interface RecognitionResultList {
  length: number;
  [i: number]: { isFinal: boolean; 0: { transcript: string } };
}

export interface RecognitionLike {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((e: { results: RecognitionResultList }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

export interface VoiceInputEnv {
  Recognition: (new () => RecognitionLike) | undefined;
  isIosPwa: boolean;
  lang: string;
  toast: (message: string) => void;
}

const MESSAGES = {
  unsupported: {
    en: "Voice input isn't available in this browser — use the keyboard's dictation (🎤) instead",
    ja: "このブラウザでは音声入力が使えません。キーボードの音声入力（🎤）をご利用ください",
  },
  denied: {
    en: "Microphone permission was denied. Allow microphone access in your browser settings to use voice input.",
    ja: "マイクの使用が許可されていません。ブラウザの設定でマイクへのアクセスを許可してください。",
  },
  failed: {
    en: "Voice input stopped unexpectedly. Please try again.",
    ja: "音声入力が中断されました。もう一度お試しください。",
  },
} as const;

export function voiceInputMessage(key: keyof typeof MESSAGES, lang: string): string {
  return MESSAGES[key][lang.startsWith("ja") ? "ja" : "en"];
}

export function detectVoiceInputEnv(): VoiceInputEnv {
  const w = window as unknown as {
    SpeechRecognition?: new () => RecognitionLike;
    webkitSpeechRecognition?: new () => RecognitionLike;
  };
  const nav = navigator as Navigator & { standalone?: boolean };
  const isIos =
    /iPad|iPhone|iPod/.test(nav.userAgent) ||
    (nav.platform === "MacIntel" && nav.maxTouchPoints > 1);
  const standalone =
    nav.standalone === true ||
    window.matchMedia?.("(display-mode: standalone)").matches === true;
  const docLang = (document.documentElement.lang || "en").toLowerCase();
  return {
    Recognition: w.SpeechRecognition || w.webkitSpeechRecognition,
    isIosPwa: isIos && standalone,
    lang: docLang.startsWith("ja") ? "ja-JP" : "en-US",
    toast: (m) => showToast(m, "warning", 6000),
  };
}

const active = new WeakMap<HTMLElement, RecognitionLike>();

/** Start dictation into `input`, or stop it if `button` is already recording. */
export function toggleVoiceInput(
  input: HTMLTextAreaElement | HTMLInputElement,
  button: HTMLElement,
  env: VoiceInputEnv = detectVoiceInputEnv(),
): RecognitionLike | null {
  const running = active.get(button);
  if (running) {
    running.stop();
    return running;
  }
  if (!env.Recognition || env.isIosPwa) {
    env.toast(voiceInputMessage("unsupported", env.lang));
    return null;
  }

  const rec = new env.Recognition();
  rec.lang = env.lang;
  rec.interimResults = true;
  rec.continuous = true;

  const base = input.value.trim();
  const setRecording = (on: boolean): void => {
    button.classList.toggle("recording", on);
    button.setAttribute("aria-pressed", String(on));
  };

  rec.onresult = (e) => {
    let spoken = "";
    for (let i = 0; i < e.results.length; i++)
      spoken += e.results[i][0].transcript;
    input.value = base && spoken ? `${base} ${spoken}` : base || spoken;
    input.dispatchEvent(new Event("input", { bubbles: true }));
  };
  rec.onerror = (e) => {
    if (e.error === "not-allowed" || e.error === "service-not-allowed") {
      env.toast(voiceInputMessage("denied", env.lang));
    } else if (e.error !== "aborted" && e.error !== "no-speech") {
      env.toast(voiceInputMessage("failed", env.lang));
    }
  };
  rec.onend = () => {
    active.delete(button);
    setRecording(false);
  };

  try {
    rec.start();
  } catch {
    env.toast(voiceInputMessage("unsupported", env.lang));
    return null;
  }
  active.set(button, rec);
  setRecording(true);
  return rec;
}
