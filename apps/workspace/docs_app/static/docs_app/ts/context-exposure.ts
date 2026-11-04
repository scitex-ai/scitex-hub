/** Browser-only Dev report viewer; delegated handlers also support Docs swaps. */
import { MAX_REPORT_BYTES, parseContextReport } from "./_context-report";
import { clearContextReport, renderContextReport } from "./_context-report-view";
import "../css/docs-context-exposure.css";
const generations = new WeakMap<HTMLElement, number>();
function invalidate(root: HTMLElement): number {
  const next = (generations.get(root) || 0) + 1; generations.set(root, next); return next;
}
function show(root: HTMLElement, text: string): void {
  const status = root.querySelector<HTMLElement>("[data-context-status]")!;
  clearContextReport(root);
  try { renderContextReport(root, parseContextReport(text)); status.textContent = "Report displayed locally. Nothing was uploaded or saved."; }
  catch (error) { status.textContent = error instanceof Error ? error.message : "Invalid context report."; }
}
document.addEventListener("click", event => {
  const target = event.target instanceof Element ? event.target.closest<HTMLButtonElement>("[data-context-read],[data-context-clear]") : null;
  const root = target?.closest<HTMLElement>("[data-context-report-viewer]");
  if (!target || !root) return;
  invalidate(root);
  const textarea = root.querySelector<HTMLTextAreaElement>("[data-context-json]")!;
  if (target.hasAttribute("data-context-clear")) {
    textarea.value = ""; root.querySelector<HTMLInputElement>("[data-context-file]")!.value = "";
    clearContextReport(root); root.querySelector<HTMLElement>("[data-context-status]")!.textContent = "No report loaded. The viewer has not measured this browser or your agent.";
  } else show(root, textarea.value);
});
document.addEventListener("change", async event => {
  const input = event.target;
  if (!(input instanceof HTMLInputElement) || !input.matches("[data-context-file]")) return;
  const root = input.closest<HTMLElement>("[data-context-report-viewer]")!, file = input.files?.[0];
  if (!file) return;
  const generation = invalidate(root);
  if (file.size > MAX_REPORT_BYTES) { clearContextReport(root); root.querySelector<HTMLElement>("[data-context-status]")!.textContent = "Choose a report of at most 2 MiB."; return; }
  try {
    const text = await file.text();
    if (root.isConnected && generations.get(root) === generation && input.files?.[0] === file) show(root, text);
  } catch { if (root.isConnected && generations.get(root) === generation) { clearContextReport(root); root.querySelector<HTMLElement>("[data-context-status]")!.textContent = "The local file could not be read."; } }
});
