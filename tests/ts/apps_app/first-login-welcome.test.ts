import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { initFirstLoginWelcome } from "../../../apps/workspace/apps_app/static/apps_app/ts/_launcher/first-login-welcome";

function surface(username = "alice"): HTMLElement {
  document.body.dataset.userAuthenticated = "true";
  document.body.dataset.currentUsername = username;
  document.body.innerHTML = `
    <section data-first-login-welcome>
      <button type="button" data-first-login-dismiss>Close ×</button>
      <a href="/new/" data-action="create-project">Create project</a>
    </section>
    <div class="launcher-section-head"><h2>All apps</h2></div>
    <div id="launcher-grid"><button id="app">An app</button></div>`;
  return document.querySelector<HTMLElement>("[data-first-login-welcome]")!;
}

describe("first-login welcome dismissal", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = "";
    delete document.body.dataset.currentUsername;
    delete document.body.dataset.userAuthenticated;
  });

  it("closes immediately, remembers only this user and returns focus to apps", () => {
    const welcome = surface();
    initFirstLoginWelcome();
    welcome.querySelector<HTMLButtonElement>("button")!.click();
    expect({ hidden: welcome.hidden, remembered: localStorage.getItem("scitex-first-login-welcome-dismissed:alice"), focus: document.activeElement?.id })
      .toEqual({ hidden: true, remembered: "true", focus: "launcher-grid" });
  });

  it("honors a returning user's dismissal", () => {
    localStorage.setItem("scitex-first-login-welcome-dismissed:alice", "true");
    const welcome = surface();
    initFirstLoginWelcome();
    expect(welcome.hidden).toBe(true);
  });

  it("keeps another signed-in user's welcome visible", () => {
    localStorage.setItem("scitex-first-login-welcome-dismissed:alice", "true");
    const welcome = surface("bob");
    initFirstLoginWelcome();
    expect(welcome.hidden).toBe(false);
  });

  it("closes when browser storage refuses reads and writes", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
    const welcome = surface();
    initFirstLoginWelcome();
    welcome.querySelector<HTMLButtonElement>("button")!.click();
    expect(welcome.hidden).toBe(true);
  });

  it("supports Escape from within the card", () => {
    const welcome = surface();
    initFirstLoginWelcome();
    welcome.querySelector("button")!.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
    expect(welcome.hidden).toBe(true);
  });

  it("does not consume an Escape already handled by a child", () => {
    const welcome = surface();
    initFirstLoginWelcome();
    const event = new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true });
    event.preventDefault();
    welcome.querySelector("button")!.dispatchEvent(event);
    expect(welcome.hidden).toBe(false);
  });

  it("does not dismiss for an unrelated app's Escape", () => {
    const welcome = surface();
    initFirstLoginWelcome();
    document.getElementById("app")!.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(welcome.hidden).toBe(false);
  });

  it("never persists a shared anonymous dismissal", () => {
    const welcome = surface();
    document.body.dataset.userAuthenticated = "false";
    initFirstLoginWelcome();
    welcome.querySelector<HTMLButtonElement>("button")!.click();
    expect({ hidden: welcome.hidden, storageKeys: Object.keys(localStorage) }).toEqual({ hidden: true, storageKeys: [] });
  });

  it("prevents the dismiss click from activating page handlers without blocking later app clicks", () => {
    const welcome = surface();
    const handler = vi.fn();
    document.body.addEventListener("click", handler);
    try {
      initFirstLoginWelcome();
      welcome.querySelector<HTMLButtonElement>("button")!.click();
      document.getElementById("app")!.click();
      expect(handler).toHaveBeenCalledTimes(1);
    } finally {
      document.body.removeEventListener("click", handler);
    }
  });
});
