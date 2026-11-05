import { afterEach, describe, expect, it } from "vitest";
import { initOpenSourceTabs } from "../../../apps/infra/public_app/static/public_app/ts/landing/opensource-tabs";

function mount(): HTMLButtonElement[] {
  document.body.innerHTML = `<nav data-oss-tabs hidden>
    <button id="a" role="tab" aria-controls="pa">Platform</button>
    <button id="b" role="tab" aria-controls="pb">Research</button>
  </nav><section id="pa"><h3>Platform</h3>A</section>
  <section id="pb"><h3>Research</h3>B</section>`;
  return [...document.querySelectorAll<HTMLButtonElement>("button")];
}

afterEach(() => document.body.replaceChildren());

describe("source repository tabs", () => {
  it("keeps all groups readable until initialization, then selects one group", () => {
    const tabs = mount();
    expect(document.querySelectorAll("section[hidden]")).toHaveLength(0);
    initOpenSourceTabs();
    expect(document.querySelector("nav")!.hidden).toBe(false);
    expect(tabs.map(tab => tab.getAttribute("aria-selected"))).toEqual(["true", "false"]);
    tabs[1].click();
    expect(document.querySelector<HTMLElement>("#pa")!.hidden).toBe(true);
    expect(document.querySelector<HTMLElement>("#pb")!.hidden).toBe(false);
    expect(tabs.map(tab => tab.tabIndex)).toEqual([-1, 0]);
  });

  it("supports keyboard wrap, Home and End without duplicate setup", () => {
    const tabs = mount();
    initOpenSourceTabs();
    initOpenSourceTabs();
    tabs[0].dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    expect(document.activeElement).toBe(tabs[1]);
    tabs[1].dispatchEvent(new KeyboardEvent("keydown", { key: "Home", bubbles: true }));
    expect(document.activeElement).toBe(tabs[0]);
    tabs[0].dispatchEvent(new KeyboardEvent("keydown", { key: "End", bubbles: true }));
    expect(document.activeElement).toBe(tabs[1]);
    expect(document.querySelectorAll('button[aria-selected="true"]')).toHaveLength(1);
  });
});
