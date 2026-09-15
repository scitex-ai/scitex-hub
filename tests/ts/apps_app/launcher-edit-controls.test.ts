import { afterEach, describe, expect, it, vi } from "vitest";

import { LauncherEditControls } from "@apps_app/_launcher/edit-controls";

function grid(): HTMLElement {
  document.body.innerHTML = `<div id="launcher-grid" class="edit-mode">
    <a class="launcher-tile" data-module="community" data-label="Community">
      <span role="button" tabindex="-1" class="launcher-edit-control launcher-uninstall-control">-</span>
    </a>
  </div>`;
  return document.getElementById("launcher-grid") as HTMLElement;
}

afterEach(() => vi.restoreAllMocks());

describe("LauncherEditControls", () => {
  it("makes controls keyboard reachable only while edit mode is active", () => {
    const host = grid();
    new LauncherEditControls(host, vi.fn()).init();
    expect(host.querySelector<HTMLElement>(".launcher-edit-control")?.tabIndex).toBe(0);
  });

  it("confirms uninstall and removes the tile after the authenticated endpoint succeeds", async () => {
    const host = grid();
    const rebalance = vi.fn();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    }));
    new LauncherEditControls(host, rebalance).init();
    host.querySelector<HTMLElement>(".launcher-uninstall-control")?.click();
    await vi.waitFor(() => expect(host.querySelector(".launcher-tile")).toBeNull());
    expect(fetch).toHaveBeenCalledWith(
      "/apps/store/api/community/uninstall/",
      expect.objectContaining({ method: "POST", credentials: "same-origin" }),
    );
    expect(rebalance).toHaveBeenCalledOnce();
  });
});
