import { beforeEach, expect, test, vi } from "vitest";
import fixture from "../fixtures/context-exposure/dev-source-report.json";
import { parseContextReport, validateContextReport } from "../../apps/workspace/docs_app/static/docs_app/ts/_context-report";
import { renderContextReport } from "../../apps/workspace/docs_app/static/docs_app/ts/_context-report-view";
import "../../apps/workspace/docs_app/static/docs_app/ts/context-exposure";
const copy = () => JSON.parse(JSON.stringify(fixture));
const markup = `<section data-context-report-viewer><input type="file" data-context-file><textarea data-context-json></textarea><button data-context-read>View report</button><button data-context-clear>Clear</button><p role="status" data-context-status>No report loaded.</p><div hidden data-context-output>${["total-bytes","total-characters","instruction-bytes","instruction-raw-bytes","instruction-raw-characters","framing-bytes"].map(n=>`<span data-context-value="${n}"></span>`).join("")}<table><tbody data-context-owner-rows></tbody></table></div></section>`;
beforeEach(() => { document.body.innerHTML = markup; });
test("actual Dev-produced Unicode fixture preserves unknown ownership and framing", () => {
  const result = parseContextReport(JSON.stringify(fixture));
  expect(result.total.utf8_bytes).toBeGreaterThan(result.total.characters);
  expect(result.instructions.utf8_bytes).toBeGreaterThan(result.instructionsRaw.utf8_bytes);
  expect(result.framing.utf8_bytes).toBeGreaterThan(0);
  expect(result.owners.map(r=>r.owner)).toContain("unattributed");
});
test.each([
  ["unsupported schema", (r:any)=>{r.schema_version="other/1";}],
  ["installed catalog mislabeled as context", (r:any)=>{r.scope="installed_catalog";}],
  ["invented token count", (r:any)=>{r.tokens=100;}],
  ["invented total context", (r:any)=>{r.client_total_context=1000;}],
  ["negative count", (r:any)=>{r.total.characters=-1;}],
  ["unsafe integer", (r:any)=>{r.total.utf8_bytes=Number.MAX_SAFE_INTEGER+1;}],
  ["aggregate mismatch", (r:any)=>{r.packages['scitex-sdk'].skill_headers++;}],
  ["framing mismatch", (r:any)=>{r.total.utf8_bytes++;}],
  ["missing owner falsely declared", (r:any)=>{r.items[1].ownership="declared";}],
  ["duplicate identity", (r:any)=>{r.items.push({...r.items[0]});}],
  ["reserved unknown owner", (r:any)=>{r.items[0].owner="unattributed";}],
])("refuses %s", (_name, change) => { const report=copy();change(report);expect(()=>validateContextReport(report)).toThrow(); });
test("malformed JSON error does not echo private pasted content", () => {
  expect(()=>parseContextReport('{"private":"SECRET-SENTINEL" broken')).toThrow("The file is not valid JSON.");
});
test("oversized input is rejected before JSON parsing", () => { expect(()=>parseContextReport(" ".repeat(2*1024*1024+1))).toThrow("at most 2 MiB"); });
test("owner strings are text nodes and bars are relative owner sizes, not total context", () => {
  const report=copy(), owner='<img src=x onerror="window.EXECUTED=true">';
  report.items[0].owner=owner;report.packages[owner]=report.packages['scitex-scholar'];delete report.packages['scitex-scholar'];
  renderContextReport(document.querySelector<HTMLElement>('[data-context-report-viewer]')!,validateContextReport(report));
  expect(document.querySelector("img")).toBeNull();expect(document.body.textContent).toContain(owner);
  const maximum=Math.max(...Object.values(report.packages).map((r:any)=>r.utf8_bytes));
  expect([...document.querySelectorAll("progress")].every(p=>p.max===maximum)).toBe(true);
});
test("delegated viewer works after a Docs fragment replacement without network or storage writes", () => {
  const fetch=vi.spyOn(window,"fetch"), storage=vi.spyOn(Storage.prototype,"setItem");
  for(let index=0;index<2;index++) {
    document.body.innerHTML=markup;
    (document.querySelector('[data-context-json]') as HTMLTextAreaElement).value=JSON.stringify(fixture);
    (document.querySelector('[data-context-read]') as HTMLButtonElement).click();
    expect((document.querySelector('[data-context-output]') as HTMLElement).hidden).toBe(false);
    expect(document.querySelectorAll('progress')).toHaveLength(3);
    (document.querySelector('[data-context-clear]') as HTMLButtonElement).click();
    expect((document.querySelector('[data-context-output]') as HTMLElement).hidden).toBe(true);
    expect([...document.querySelectorAll('[data-context-value]')].every(field=>field.textContent==="")).toBe(true);
  }
  expect(fetch).not.toHaveBeenCalled();expect(storage).not.toHaveBeenCalled();fetch.mockRestore();storage.mockRestore();
});
test("a late local-file read cannot repopulate a cleared viewer", async () => {
  const input=document.querySelector<HTMLInputElement>('[data-context-file]')!;
  let complete!: (text:string)=>void;
  const pending=new Promise<string>(resolve=>{complete=resolve;});
  const file={size:100,text:()=>pending};
  // A deterministic chooser read held across Clear; no service/network mock.
  Object.defineProperty(input,"files",{configurable:true,value:[file]});
  input.dispatchEvent(new Event("change",{bubbles:true}));
  (document.querySelector('[data-context-clear]') as HTMLButtonElement).click();
  complete(JSON.stringify(fixture));await Promise.resolve();await Promise.resolve();
  expect((document.querySelector('[data-context-output]') as HTMLElement).hidden).toBe(true);
  expect(document.querySelector('[data-context-status]')!.textContent).toContain('No report loaded');
});
test("an arbitrary JSON owner key cannot mutate object prototypes", () => {
  const report=copy(), owner="__proto__";
  report.items[0].owner=owner;
  Object.defineProperty(report.packages,owner,{enumerable:true,value:report.packages['scitex-scholar']});delete report.packages['scitex-scholar'];
  const result=parseContextReport(JSON.stringify(report));
  expect(result.owners.map(row=>row.owner)).toContain(owner);
  renderContextReport(document.querySelector<HTMLElement>('[data-context-report-viewer]')!,result);
  expect(document.querySelector('tbody')!.textContent).toContain(owner);
  expect(({} as Record<string,unknown>).mcp_tools).toBeUndefined();
  expect(Object.prototype.hasOwnProperty.call(Object.prototype,"mcp_tools")).toBe(false);
});
