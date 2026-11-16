/** Copy the current page's existing Markdown export; never the navigation UI. */
export function initDocsCopy(workspace: HTMLElement): void {
  const button = workspace.querySelector<HTMLButtonElement>("#docs-copy-page");
  if (!button) return;
  let reset: ReturnType<typeof setTimeout> | undefined;
  button.addEventListener("click", async () => {
    const link = workspace.querySelector<HTMLAnchorElement>("#docs-download-page");
    const label = button.querySelector("span");
    if (!link || !label) return;
    if (reset) clearTimeout(reset);
    button.disabled = true;
    try {
      const response = await fetch(link.href);
      if (!response.ok) throw new Error("The documentation could not be downloaded.");
      if (!response.headers.get("content-type")?.includes("text/markdown")) throw new Error("The server did not return Markdown.");
      const text = await response.text();
      await navigator.clipboard.writeText(text);
      label.textContent = "Copied";
      button.title = "This page's Markdown was copied to the clipboard";
    } catch (error) {
      label.textContent = "Copy failed";
      button.title = error instanceof Error ? error.message : "Clipboard unavailable; use Download";
    } finally {
      button.disabled = false;
      reset = setTimeout(() => { label.textContent = "Copy Markdown"; button.title = "Copy this page as Markdown"; }, 2500);
    }
  });
}
