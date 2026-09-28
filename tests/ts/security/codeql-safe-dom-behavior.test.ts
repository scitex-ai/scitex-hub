import { describe, expect, it } from "vitest";
import { renderSectionDropdown } from "@writer_app/utils/_section-dropdown/rendering";
import { renderMedia } from "@/components/_global-ai-chat/media-renderer";
import { safeSameOriginNavigationUrl } from "@/components/sidebar";
import { sanitizeLogValue } from "@/components/workspace-viewer/_security";

describe("safe DOM construction", () => {
  it("keeps section labels and identifiers inert", () => {
    const fragment = renderSectionDropdown(
      [
        {
          id: 'bad\" onclick="alert(1)',
          label: '<img src=x onerror="alert(1)">',
        },
      ],
      "manuscript",
    );
    const host = document.createElement("div");
    host.appendChild(fragment);
    expect(host.querySelector("img")).toBeNull();
    expect(host.querySelector(".section-item-name")?.textContent).toBe(
      '<img src=x onerror="alert(1)">',
    );
    expect(
      host.querySelector(".section-item")?.getAttribute("onclick"),
    ).toBeNull();
  });

  it("encodes media routes and renders filenames as text", () => {
    const element = renderMedia(
      { type: "pdf", path: 'report\"><img src=x>.pdf', ext: ".pdf" },
      "user/name",
      "project?admin=true",
    );
    const link = element.querySelector("a")!;
    expect(link.textContent).toBe('report\"><img src=x>.pdf');
    expect(link.querySelector("img")).toBeNull();
    expect(link.getAttribute("href")).toContain(
      "user%2Fname/project%3Fadmin%3Dtrue",
    );
  });

  it("rejects script and cross-origin sidebar navigation", () => {
    expect(safeSameOriginNavigationUrl("javascript:alert(1)")).toBeNull();
    expect(safeSameOriginNavigationUrl("https://attacker.invalid/")).toBeNull();
    expect(safeSameOriginNavigationUrl("/apps/writer/")).toBe(
      `${window.location.origin}/apps/writer/`,
    );
  });

  it("removes line-breaking control characters from log values", () => {
    const value = sanitizeLogValue("safe\r\nFORGED\u0000entry\u2028next");
    expect(value).not.toMatch(/[\r\n\u2028\u2029\u0000]/);
    expect(value).toContain("FORGED?entry next");
  });
});
