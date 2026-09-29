/** Setup-provider failures must escape the floating Chat iframe safely. */

import { beforeEach, describe, expect, it, vi } from "vitest";

const navigationBridge = vi.hoisted(() => ({
  postParentNavigation: vi.fn(() => true),
}));

vi.mock("@/components/_site-dock/embed-navigation", async (importOriginal) => {
  const actual = await importOriginal<
    typeof import("../../../../static/shared/ts/components/_site-dock/embed-navigation")
  >();
  return {
    ...actual,
    postParentNavigation: navigationBridge.postParentNavigation,
  };
});

import {
  AIPanelChatMode,
  type ChatModeRefs,
} from "@/components/_global-ai-chat/chat-mode";

function refs(messagesEl: HTMLElement, inputEl: HTMLTextAreaElement): ChatModeRefs {
  return {
    messagesEl,
    inputEl,
    sendBtn: document.createElement("button"),
    speakBtn: null,
    micBtn: null,
    sttModelSelect: null,
    modelBadge: null,
    volBars: [],
    imagePreviewEl: null,
    imageFileInput: null,
    cameraBtn: null,
    sketchBtn: null,
  };
}

describe("AI provider setup action", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    localStorage.clear();
    navigationBridge.postParentNavigation.mockClear();
  });

  it("requests typed parent navigation instead of following inside the iframe", async () => {
    const messages = document.createElement("div");
    const input = document.createElement("textarea");
    input.value = "hello";
    document.body.append(messages, input);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        body: {},
        status: 400,
        json: async () => ({
          error: "No provider configured.",
          settings_url: "/accounts/settings/ai-providers/",
        }),
      })),
    );

    const chat = new AIPanelChatMode();
    chat.init(refs(messages, input), {}, false);
    await chat.send();

    const link = messages.querySelector<HTMLAnchorElement>(
      ".stx-shell-ai-error-action",
    );
    expect(link).not.toBeNull();
    const click = new MouseEvent("click", {
      bubbles: true,
      cancelable: true,
      button: 0,
    });
    link!.dispatchEvent(click);

    expect(click.defaultPrevented).toBe(true);
    expect(navigationBridge.postParentNavigation).toHaveBeenCalledTimes(1);
    expect(navigationBridge.postParentNavigation).toHaveBeenCalledWith(
      "/accounts/settings/ai-providers/",
    );
  });

  it("does not render a server-provided cross-origin setup link", async () => {
    const messages = document.createElement("div");
    const input = document.createElement("textarea");
    input.value = "hello";
    document.body.append(messages, input);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        body: {},
        status: 400,
        json: async () => ({
          error: "No provider configured.",
          settings_url: "https://attacker.example/steal",
        }),
      })),
    );

    const chat = new AIPanelChatMode();
    chat.init(refs(messages, input), {}, false);
    await chat.send();

    expect(messages.querySelector(".stx-shell-ai-error-action")).toBeNull();
    expect(navigationBridge.postParentNavigation).not.toHaveBeenCalled();
  });
});
