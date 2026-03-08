/**
 * Text-to-speech utilities for the AI Agent panel.
 * Calls /apps/llm/api/tts/ (delegates to scitex.audio) with browser
 * speechSynthesis as fallback when the server endpoint is unavailable.
 */

export function cleanForSpeech(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, " code block. ")
    .replace(/`[^`]+`/g, "")
    .replace(/\*\*?([^*]+)\*\*?/g, "$1")
    .replace(/#+\s*/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/https?:\/\/\S+/g, " link ")
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Speak text via server TTS and return the playing Audio element so the
 * caller can stop it on demand.  Falls back to window.speechSynthesis.
 */
export async function speakText(
  text: string,
  csrf: string,
): Promise<HTMLAudioElement | null> {
  const clean = cleanForSpeech(text);
  if (!clean) return null;

  try {
    const r = await fetch("/apps/llm/api/tts/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf,
      },
      body: JSON.stringify({ text: clean }),
    });
    if (!r.ok) throw new Error(`TTS ${r.status}`);
    const url = URL.createObjectURL(await r.blob());
    const audio = new Audio(url);
    audio.onended = () => URL.revokeObjectURL(url);
    await audio.play();
    return audio;
  } catch {
    // Fallback: browser built-in TTS (no server needed)
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(new SpeechSynthesisUtterance(clean));
    }
    return null;
  }
}
