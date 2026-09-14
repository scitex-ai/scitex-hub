/**
 * Chat mic button never fails silently (operator iPhone report 2026-09-14:
 * tapping the mic on the full-page Chat did nothing).
 */

import { describe, it, expect } from "vitest";

import {
  toggleVoiceInput,
  type RecognitionLike,
  type VoiceInputEnv,
} from "@/components/voice-input";

function makeEnv(overrides: Partial<VoiceInputEnv>): {
  env: VoiceInputEnv;
  toasts: string[];
} {
  const toasts: string[] = [];
  const env: VoiceInputEnv = {
    Recognition: undefined,
    isIosPwa: false,
    lang: "en-US",
    toast: (m) => toasts.push(m),
    ...overrides,
  };
  return { env, toasts };
}

class FakeRecognition implements RecognitionLike {
  lang = "";
  interimResults = false;
  continuous = false;
  onresult = null;
  onerror = null;
  onend = null;
  started = false;
  start(): void {
    this.started = true;
  }
  stop(): void {}
}

describe("chat voice input", () => {
  it("tells the user to use keyboard dictation when recognition is unsupported", () => {
    // Arrange
    const { env, toasts } = makeEnv({ lang: "ja-JP" });
    // Act
    toggleVoiceInput(
      document.createElement("textarea"),
      document.createElement("button"),
      env,
    );
    // Assert
    expect(toasts).toEqual([
      "このブラウザでは音声入力が使えません。キーボードの音声入力（🎤）をご利用ください",
    ]);
  });

  it("starts recognition in the UI language when supported", () => {
    // Arrange
    const { env } = makeEnv({ Recognition: FakeRecognition, lang: "ja-JP" });
    // Act
    const rec = toggleVoiceInput(
      document.createElement("textarea"),
      document.createElement("button"),
      env,
    ) as FakeRecognition;
    // Assert
    expect([rec.started, rec.lang]).toEqual([true, "ja-JP"]);
  });
});
