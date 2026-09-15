import { afterEach, describe, expect, it, vi } from "vitest";

import { LauncherPopover } from "@apps_app/_launcher/popover";

function tile(): HTMLElement {
  const host = document.createElement("div");
  host.innerHTML = `<a class="launcher-tile" href="/apps/stats/"
    data-module="stats" data-availability="available"
    data-detail-url="/apps/store/stats/">Stats</a>`;
  document.body.appendChild(host);
  const app = host.firstElementChild as HTMLElement;
  vi.spyOn(app, "getBoundingClientRect").mockReturnValue({
    x: 20, y: 20, top: 20, left: 20, right: 120, bottom: 120,
    width: 100, height: 100, toJSON: () => ({}),
  });
  return app;
}

afterEach(() => {
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

describe("LauncherPopover", () => {
  it("uses the same display editor as mobile and removes obsolete sidebar pinning", () => {
    const app = tile();
    const onEditDisplay = vi.fn();
    const popover = new LauncherPopover(document.body, {
      onRearrange: vi.fn(),
      onEditDisplay,
    });

    popover.open(app);
    const menu = document.querySelector<HTMLElement>(".launcher-popover");
    expect(menu?.textContent).toContain("Open");
    expect(menu?.textContent).toContain("Edit Display…");
    expect(menu?.textContent).toContain("Rearrange apps");
    expect(menu?.textContent).toContain("View in App Store");
    expect(menu?.textContent).not.toContain("sidebar");
    expect(menu?.textContent).not.toContain("Uninstall");

    Array.from(menu?.querySelectorAll("button") ?? [])
      .find((button) => button.textContent?.includes("Edit Display"))
      ?.click();
    expect(onEditDisplay).toHaveBeenCalledWith(app);
  });
});
