import { mountProjectPickers } from "@scitex/sdk/ui/ts/app/project-selector";

/** Host-owned fragment metadata; SDK alone renders/validates the action. */
export const API_DOCS_HEADER = "X-SciTeX-API-Docs-URL";
const ATTRIBUTE = "data-stx-api-docs-url";

export function prepareModuleDocumentation(pane: HTMLElement, response: Response): void {
  // Empty is intentional: removing the attribute could inherit the old body owner.
  pane.setAttribute(ATTRIBUTE, response.headers.get(API_DOCS_HEADER) ?? "");
}

export function mountModuleHeader(pane: HTMLElement): void {
  // Reinserted ES modules may already be cached. Use the SDK's public lifecycle
  // port; it owns instance cleanup, picker adoption and ambiguity rules.
  (window as Window & { stxAppHeader?: { mount(root: ParentNode): unknown } })
    .stxAppHeader?.mount(pane);
  // Declarative picker scripts can also be cached. The existing SDK port
  // requires a provider URL and honors its mounted marker, so it does not
  // create a new provider or duplicate an existing controller.
  mountProjectPickers(pane);
}
