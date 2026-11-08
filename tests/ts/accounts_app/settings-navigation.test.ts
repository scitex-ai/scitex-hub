import { describe, expect, it } from "vitest";
import { createSettingsDestinationResolver, localSettingsPagePath } from "../../../apps/infra/accounts_app/static/accounts_app/ts/settings-navigation";

const origin = "https://scitex.example";

describe("mobile settings local destinations", () => {
  it.each([
    "/accounts/settings/profile/",
    "/accounts/settings/appearance/",
    "/ywatanabe/",
    "/accounts/settings/privacy/?tab=analytics#choices",
  ])("preserves the local destination %s", (path) => {
    expect(localSettingsPagePath(path, origin)).toBe(path);
  });

  it.each([
    "https://external.example/",
    "https://scitex.example/accounts/settings/profile/",
    "//external.example/",
    "/folder/..//external.example/",
    "/%2e//external.example/",
    "/.%2e//external.example/",
    "/\\external.example/",
    "\\\\external.example/",
    "javascript:alert(1)",
    "data:text/html,external",
    "accounts/settings/profile/",
    " /accounts/settings/profile/",
    "/accounts/\nsettings/",
    "/accounts/\tsettings/",
    "",
  ])("refuses a noncanonical or external destination %j", (path) => {
    expect(localSettingsPagePath(path, origin)).toBeNull();
  });
});


describe("mobile settings captured destinations", () => {
  function setup() {
    const option = document.createElement("option");
    option.value = "/accounts/settings/profile/";
    option.dataset.group = "personal";
    return { option, resolve: createSettingsDestinationResolver([option], origin) };
  }

  it("resolves an original visible option in its original group", () => {
    const { option, resolve } = setup();
    expect(resolve(option, "personal")).toBe("/accounts/settings/profile/");
  });

  it.each(["https://external.example/", "/admin/"])("rejects an original option changed to %s", (path) => {
    const { option, resolve } = setup();
    option.value = path;
    expect(resolve(option, "personal")).toBeNull();
  });

  it("rejects an inserted option even when it copies an approved value", () => {
    const { option, resolve } = setup();
    const inserted = option.cloneNode(true) as HTMLOptionElement;
    expect(resolve(inserted, "personal")).toBeNull();
  });

  it("rejects an original option moved to a different group", () => {
    const { option, resolve } = setup();
    option.dataset.group = "authentication";
    expect(resolve(option, "authentication")).toBeNull();
  });

  it("rejects an original hidden option", () => {
    const { option, resolve } = setup();
    option.hidden = true;
    expect(resolve(option, "personal")).toBeNull();
  });

  it("rejects a selection from another group", () => {
    const { option, resolve } = setup();
    expect(resolve(option, "authentication")).toBeNull();
  });

  it("rejects an absent selection", () => {
    const { resolve } = setup();
    expect(resolve(null, "personal")).toBeNull();
  });
});
