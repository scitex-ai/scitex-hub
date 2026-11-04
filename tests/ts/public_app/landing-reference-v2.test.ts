import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { initLandingCarousels } from "@public_app/landing/reference-v2";

const markup = `
  <section data-landing-carousel tabindex="0">
    <button type="button" data-carousel-prev>Previous</button>
    <button type="button" data-carousel-rotation data-pause-label="Pause automatic screenshots" data-resume-label="Resume automatic screenshots">
      <span data-carousel-status></span><i data-carousel-rotation-icon></i>
    </button>
    <button type="button" data-carousel-next>Next</button>
    <div data-carousel-track>
      <figure data-carousel-slide>Hub</figure>
      <figure data-carousel-slide hidden>Scholar</figure>
      <figure data-carousel-slide hidden>Writer</figure>
    </div>
    <div role="tablist">
      <button type="button" data-carousel-dot="0" aria-selected="true">Hub</button>
      <button type="button" data-carousel-dot="1" aria-selected="false">Scholar</button>
      <button type="button" data-carousel-dot="2" aria-selected="false">Writer</button>
    </div>
  </section>`;

function pointer(type: string, clientX: number): Event {
  const event = new Event(type, { bubbles: true });
  Object.defineProperty(event, "clientX", { value: clientX });
  return event;
}

function actualGalleryMarkup(): string {
  const source = readFileSync(resolve(process.cwd(), "apps/infra/public_app/templates/public_app/landing_partials/landing_app_gallery.html"), "utf8");
  const manifest = JSON.parse(readFileSync(resolve(process.cwd(), "apps/infra/public_app/static/public_app/images/landing-v2/product-captures-eleven-apps-20261103.json"), "utf8"));
  const host = document.createElement("div");
  host.innerHTML = source.replace(/{%[\s\S]*?%}/g, "");
  // Unit fixture for the rendered tab contract. Actual Django rendering and
  // public metadata projection are checked by test_landing_capture_tabs.py.
  const tabs = host.querySelector<HTMLElement>("[data-carousel-tabs]")!;
  tabs.replaceChildren();
  const categoryRow = document.createElement("div");
  categoryRow.dataset.carouselCategories = "";
  categoryRow.setAttribute("role", "tablist");
  tabs.append(categoryRow);
  const groups = new Map<string, HTMLElement>();
  const captures = [...manifest.captures].sort((a, b) => a.gallery_slide_index - b.gallery_slide_index);
  for (const app of captures) {
    let panel = groups.get(app.gallery_category);
    if (!panel) {
      const category = document.createElement("button");
      category.dataset.carouselCategoryTab = app.gallery_category;
      category.setAttribute("role", "tab");
      category.textContent = app.gallery_category;
      categoryRow.append(category);
      panel = document.createElement("div");
      panel.dataset.carouselCategoryPanel = app.gallery_category;
      panel.hidden = groups.size > 0;
      groups.set(app.gallery_category, panel);
      tabs.append(panel);
    }
    const button = document.createElement("button");
    button.dataset.carouselDot = String(app.gallery_slide_index);
    button.dataset.carouselAppCategory = app.gallery_category;
    button.title = app.capture_version_note;
    button.textContent = app.gallery_label;
    const version = document.createElement("small");
    version.textContent = "v" + app.capture_version;
    button.append(version);
    button.setAttribute("role", "tab");
    panel.append(button);
  }
  return host.innerHTML;
}

beforeEach(() => {
  vi.useFakeTimers();
  Object.defineProperty(document, "hidden", { configurable: true, value: false });
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("landing V2 product carousel", () => {
  beforeEach(() => {
    document.body.innerHTML = markup;
  });

  it("automatically advances at six seconds and wraps to the first slide", () => {
    initLandingCarousels();
    const status = () => document.querySelector("[data-carousel-status]")?.textContent;
    expect(status()).toBe("1 / 3");
    vi.advanceTimersByTime(5999);
    expect(status()).toBe("1 / 3");
    vi.advanceTimersByTime(1);
    expect(status()).toBe("2 / 3");
    vi.advanceTimersByTime(12000);
    expect(status()).toBe("1 / 3");
  });

  it("pauses and resumes through the existing counter control", () => {
    initLandingCarousels();
    const toggle = document.querySelector<HTMLButtonElement>("[data-carousel-rotation]")!;
    toggle.click();
    vi.advanceTimersByTime(18000);
    expect(document.querySelector("[data-carousel-status]")?.textContent).toBe("1 / 3");
    expect(toggle.getAttribute("aria-label")).toBe("Resume automatic screenshots");
    toggle.click();
    vi.advanceTimersByTime(6000);
    expect(document.querySelector("[data-carousel-status]")?.textContent).toBe("2 / 3");
  });

  it("pauses while hovered or focused without losing manual navigation", () => {
    initLandingCarousels();
    const carousel = document.querySelector<HTMLElement>("[data-landing-carousel]")!;
    carousel.dispatchEvent(new Event("pointerenter"));
    vi.advanceTimersByTime(12000);
    expect(document.querySelector("[data-carousel-status]")?.textContent).toBe("1 / 3");
    document.querySelector<HTMLElement>("[data-carousel-next]")!.click();
    expect(document.querySelector("[data-carousel-status]")?.textContent).toBe("2 / 3");
    carousel.dispatchEvent(new Event("pointerleave"));
    document.querySelector<HTMLElement>("[data-carousel-next]")!.focus();
    vi.advanceTimersByTime(12000);
    expect(document.querySelector("[data-carousel-status]")?.textContent).toBe("2 / 3");
    document.querySelector<HTMLElement>("[data-carousel-next]")!.blur();
    vi.advanceTimersByTime(6000);
    expect(document.querySelector("[data-carousel-status]")?.textContent).toBe("3 / 3");
  });

  it("does not hijack Home outside category or app tabs", () => {
    initLandingCarousels();
    document.querySelector<HTMLElement>("[data-carousel-next]")!.click();
    const carousel = document.querySelector<HTMLElement>("[data-landing-carousel]")!;
    const event = new KeyboardEvent("keydown", {key: "Home", bubbles: true, cancelable: true});
    carousel.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(false);
    expect(document.querySelector("[data-carousel-status]")?.textContent).toBe("2 / 3");
  });

  it("pauses in a hidden browser tab", () => {
    initLandingCarousels();
    Object.defineProperty(document, "hidden", { configurable: true, value: true });
    document.dispatchEvent(new Event("visibilitychange"));
    vi.advanceTimersByTime(12000);
    expect(document.querySelector("[data-carousel-status]")?.textContent).toBe("1 / 3");
  });

  it("starts paused for reduced motion and allows explicit resume", () => {
    vi.stubGlobal("matchMedia", () => ({ matches: true, addEventListener: vi.fn() }));
    initLandingCarousels();
    vi.advanceTimersByTime(12000);
    expect(document.querySelector("[data-carousel-status]")?.textContent).toBe("1 / 3");
    document.querySelector<HTMLElement>("[data-carousel-rotation]")!.click();
    vi.advanceTimersByTime(6000);
    expect(document.querySelector("[data-carousel-status]")?.textContent).toBe("2 / 3");
  });

  it("moves with manual next and previous controls", () => {
    initLandingCarousels();

    document.querySelector<HTMLElement>("[data-carousel-next]")?.click();
    expect(
      document.querySelector<HTMLElement>("[data-carousel-slide]:not([hidden])")
        ?.textContent,
    ).toBe("Scholar");

    document.querySelector<HTMLElement>("[data-carousel-prev]")?.click();
    expect(
      document.querySelector<HTMLElement>("[data-carousel-slide]:not([hidden])")
        ?.textContent,
    ).toBe("Hub");
  });

  it("moves with carousel-scoped arrow keys and updates tabs", () => {
    initLandingCarousels();
    const carousel = document.querySelector<HTMLElement>(
      "[data-landing-carousel]",
    )!;

    carousel.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }),
    );

    const dots = [
      ...document.querySelectorAll<HTMLElement>("[data-carousel-dot]"),
    ];
    expect(dots.map((dot) => dot.getAttribute("aria-selected"))).toEqual([
      "false",
      "true",
      "false",
    ]);
    expect(dots.map((dot) => dot.tabIndex)).toEqual([-1, 0, -1]);
  });

  it("moves to a selected dot", () => {
    initLandingCarousels();

    document.querySelector<HTMLElement>('[data-carousel-dot="2"]')?.click();

    expect(
      document.querySelector<HTMLElement>("[data-carousel-slide]:not([hidden])")
        ?.textContent,
    ).toBe("Writer");
    expect(document.querySelector("[data-carousel-status]")?.textContent).toBe(
      "3 / 3",
    );
  });

  it("supports a horizontal swipe without hijacking small taps", () => {
    initLandingCarousels();
    const track = document.querySelector<HTMLElement>("[data-carousel-track]")!;

    track.dispatchEvent(pointer("pointerdown", 280));
    track.dispatchEvent(pointer("pointerup", 180));

    expect(
      document.querySelector<HTMLElement>("[data-carousel-slide]:not([hidden])")
        ?.textContent,
    ).toBe("Scholar");
  });
});


describe("current eleven-application template", () => {
  it("keeps all eleven actual slides reachable by keyboard, swipe and dots", () => {
    document.body.innerHTML = actualGalleryMarkup();
    const carousel = document.querySelector<HTMLElement>("[data-landing-carousel]")!;
    const slides = [...carousel.querySelectorAll<HTMLElement>("[data-carousel-slide]")];
    const dots = [...carousel.querySelectorAll<HTMLButtonElement>("[data-carousel-dot]")];
    expect(slides.map(s => s.querySelector("strong")?.textContent)).toEqual([
      "Hub", "SDK", "Agent Container", "Cards", "Storage", "Scholar", "Stats", "FigRecipe", "Writer", "Live Paper", "Agentic Journal",
    ]);
    expect(dots).toHaveLength(11);
    initLandingCarousels();
    const status = () => carousel.querySelector("[data-carousel-status]")?.textContent;
    expect(status()).toBe("1 / 11");
    dots[0].focus();
    dots[0].dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    expect(status()).toBe("2 / 11");
    expect(document.activeElement).toBe(dots[1]);
    expect(slides.map(s => s.hidden)).toEqual([true, false, true, true, true, true, true, true, true, true, true]);
    dots[1].dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    expect(status()).toBe("1 / 11");
    const track = carousel.querySelector<HTMLElement>("[data-carousel-track]")!;
    track.dispatchEvent(pointer("pointerdown", 280));
    track.dispatchEvent(pointer("pointerup", 180));
    expect(status()).toBe("2 / 11");
    document.querySelector<HTMLButtonElement>('[data-carousel-category-tab="infrastructure"]')!.click();
    dots[3].click();
    expect(status()).toBe("4 / 11");
    expect(slides[3].hidden).toBe(false);
    expect(dots.map(d => d.tabIndex)).toEqual([-1, -1, -1, 0, -1, -1, -1, -1, -1, -1, -1]);
    expect(slides.filter(s => s.getAttribute("aria-hidden") === "false")).toHaveLength(1);
  });
});


describe("two-level screenshot categories", () => {
  beforeEach(() => { document.body.innerHTML = actualGalleryMarkup(); initLandingCarousels(); });
  const category = (key: string) => document.querySelector<HTMLButtonElement>(`[data-carousel-category-tab="${key}"]`)!;
  const dot = (index: number) => document.querySelector<HTMLButtonElement>(`[data-carousel-dot="${index}"]`)!;
  const status = () => document.querySelector("[data-carousel-status]")?.textContent;
  const visibleGroup = () => [...document.querySelectorAll<HTMLElement>("[data-carousel-category-panel]")].filter(p => !p.hidden).map(p => p.dataset.carouselCategoryPanel);

  it("shows only the selected group's apps and remembers the last app per category", () => {
    expect(visibleGroup()).toEqual(["platform"]);
    dot(1).click();
    category("research").click();
    expect(status()).toBe("6 / 11");
    expect(visibleGroup()).toEqual(["research"]);
    dot(8).click();
    category("platform").click();
    expect(status()).toBe("2 / 11");
    category("research").click();
    expect(status()).toBe("9 / 11");
  });

  it("keeps app arrows and Home/End within their group", () => {
    category("research").click();
    dot(5).focus();
    dot(5).dispatchEvent(new KeyboardEvent("keydown", {key: "ArrowLeft", bubbles: true}));
    expect(status()).toBe("9 / 11");
    expect(document.activeElement).toBe(dot(8));
    dot(8).dispatchEvent(new KeyboardEvent("keydown", {key: "Home", bubbles: true}));
    expect(status()).toBe("6 / 11");
    dot(5).dispatchEvent(new KeyboardEvent("keydown", {key: "End", bubbles: true}));
    expect(status()).toBe("9 / 11");
  });

  it("navigates the category row without handing focus to an app tab", () => {
    category("platform").focus();
    category("platform").dispatchEvent(new KeyboardEvent("keydown", {key: "ArrowLeft", bubbles: true}));
    expect(visibleGroup()).toEqual(["publication"]);
    expect(status()).toBe("10 / 11");
    expect(document.activeElement).toBe(category("publication"));
  });

  it("synchronizes categories when global manual controls and swipe cross groups", () => {
    dot(1).click();
    document.querySelector<HTMLElement>("[data-carousel-next]")!.click();
    expect(status()).toBe("3 / 11");
    expect(visibleGroup()).toEqual(["infrastructure"]);
    category("research").click();
    dot(8).click();
    const track = document.querySelector<HTMLElement>("[data-carousel-track]")!;
    track.dispatchEvent(pointer("pointerdown", 280));track.dispatchEvent(pointer("pointerup", 180));
    expect(status()).toBe("10 / 11");
    expect(visibleGroup()).toEqual(["publication"]);
    expect(category("publication").getAttribute("aria-selected")).toBe("true");
  });

  it("preserves autoplay across category boundaries and wraps all eleven slides", () => {
    dot(1).click();
    vi.advanceTimersByTime(6000);
    expect(status()).toBe("3 / 11");expect(visibleGroup()).toEqual(["infrastructure"]);
    category("publication").click();dot(10).click();vi.advanceTimersByTime(6000);
    expect(status()).toBe("1 / 11");expect(visibleGroup()).toEqual(["platform"]);
  });

  it("uses captured versions and keeps source-only/mismatched evidence in tooltips", () => {
    expect(dot(6).querySelector("small")?.textContent).toBe("v1.0.0");
    expect(dot(6).title).toContain("No app-version badge");
    expect(dot(7).querySelector("small")?.textContent).toBe("v0.44.0");
    expect(dot(7).title).toContain("0.44.1");
    expect(dot(0).querySelector("small")?.textContent).toBe("v0.21.0");
  });
});

it("reveals a uniform application tab horizontally without moving the page on keyboard selection", () => {
  document.body.innerHTML = markup;
  const row = document.querySelector<HTMLElement>('[role="tablist"]')!;
  row.dataset.carouselAppTabs = "";
  Object.defineProperty(row, "clientWidth", { value: 200 });
  vi.spyOn(row, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 200, 44));
  const last = document.querySelector<HTMLButtonElement>('[data-carousel-dot="2"]')!;
  vi.spyOn(last, "getBoundingClientRect").mockImplementation(() => new DOMRect(260 - row.scrollLeft, 0, 126, 44));
  const focus = vi.spyOn(last, "focus");
  const scrollPage = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  initLandingCarousels();
  document.querySelector<HTMLButtonElement>('[data-carousel-dot="0"]')!.dispatchEvent(new KeyboardEvent("keydown", { key: "End", bubbles: true }));
  expect(row.scrollLeft).toBe(186);
  expect(document.activeElement).toBe(last);
  expect(focus).toHaveBeenCalledWith({ preventScroll: true });
  expect(scrollPage).not.toHaveBeenCalled();
});

it("keeps automatic selection visible in its application row without taking keyboard focus", () => {
  document.body.innerHTML = markup;
  const row = document.querySelector<HTMLElement>('[role="tablist"]')!;
  row.dataset.carouselAppTabs = "";
  Object.defineProperty(row, "clientWidth", { value: 200 });
  vi.spyOn(row, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 200, 44));
  const last = document.querySelector<HTMLButtonElement>('[data-carousel-dot="2"]')!;
  vi.spyOn(last, "getBoundingClientRect").mockImplementation(() => new DOMRect(260 - row.scrollLeft, 0, 126, 44));
  const focus = vi.spyOn(last, "focus");
  initLandingCarousels();
  vi.advanceTimersByTime(12000);
  expect(last.getAttribute("aria-selected")).toBe("true");
  expect(row.scrollLeft).toBe(186);
  expect(focus).not.toHaveBeenCalled();
});
