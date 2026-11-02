/** Explicit HTML methods retain native semantics; implicit legacy JS forms stay guarded. */
import { beforeEach, describe, expect, it } from "vitest";
import "@/utils/form-enter-handler";

beforeEach(() => {
  document.body.innerHTML = "";
});

function form(method: string | null): HTMLFormElement {
  document.body.innerHTML = `<form${method === null ? "" : ` method="${method}"`}><input name="q"><button type="submit">Calculate</button></form>`;
  return document.querySelector("form")!;
}

describe("explicit GET and POST submission", () => {
  it.each(["get", "GET", "post", "POST"])("keeps native %s submission available", (method) => {
    const node = form(method);
    const event = new Event("submit", { bubbles: true, cancelable: true });
    node.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(false);
  });

  it.each([null, ""])("keeps legacy implicit method %s guarded", (method) => {
    const node = form(method);
    const event = new Event("submit", { bubbles: true, cancelable: true });
    node.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
  });

  it("preserves cancellation by the owner of a JS-driven explicit GET form", () => {
    const node = form("get");
    node.addEventListener("submit", (event) => event.preventDefault());
    const event = new Event("submit", { bubbles: true, cancelable: true });
    node.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
  });

  it("routes Enter through the real GET submit button without pre-cancelling its submission", () => {
    const node = form("get");
    const observations: boolean[] = [];
    node.addEventListener("submit", (event) => {
      observations.push(event.defaultPrevented);
      event.preventDefault(); // The fixture owns navigation, after observing the shared handler.
    });
    node.querySelector("input")!.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }));
    expect(observations).toEqual([false]);
  });

  it("retains native validation before a submit-button click", () => {
    const node = form("get");
    node.querySelector("input")!.required = true;
    let submissions = 0;
    node.addEventListener("submit", (event) => { submissions += 1; event.preventDefault(); });
    node.querySelector("button")!.click();
    expect(submissions).toBe(0);
  });
});
