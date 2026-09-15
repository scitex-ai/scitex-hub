import { afterEach, describe, expect, it, vi } from "vitest";

import { LauncherEditControls } from "@apps_app/_launcher/edit-controls";

function grid(): HTMLElement {
  document.body.innerHTML = `<div id="launcher-grid" class="edit-mode">
    <a class="launcher-tile" data-module="community" data-label="Community" data-favorite="0">
      <span role="button" tabindex="-1" class="launcher-edit-control launcher-uninstall-control">-</span>
      <span class="launcher-tile-icon"><i class="fas fa-cube"></i></span>
    </a>
  </div>
  <dialog id="launcher-display-dialog"><form id="launcher-display-form">
    <input id="launcher-display-name"><input id="launcher-display-icon"><input id="launcher-display-color" type="color">
    <button id="launcher-display-favorite" type="button"></button>
  </form></dialog>`;
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

  it("adds and removes a favorite through the existing display dialog", async () => {
    const host = grid();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const controls = new LauncherEditControls(host, vi.fn());
    controls.init();
    const dialog = document.getElementById("launcher-display-dialog") as HTMLDialogElement;
    dialog.showModal = vi.fn();
    controls.open(host.querySelector(".launcher-tile") as HTMLElement);
    const button = document.getElementById("launcher-display-favorite") as HTMLButtonElement;

    expect(button.textContent).toContain("Add to Favorites");
    button.click();
    await vi.waitFor(() =>
      expect(host.querySelector<HTMLElement>(".launcher-tile")?.dataset.favorite).toBe("1"),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/apps/store/api/community/launcher-display/",
      expect.objectContaining({ body: JSON.stringify({ favorite: true }) }),
    );
    expect(host.querySelector<HTMLElement>(".launcher-tile")?.dataset.favorite).toBe("1");
    expect(button.textContent).toContain("Remove from Favorites");
  });
});
