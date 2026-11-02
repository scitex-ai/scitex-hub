/** Mount the installed SDK's filter component on initial and AJAX Me views. */
interface MountedFilter {
  readonly element: HTMLElement;
  destroy(): void;
}
interface FilterModule {
  mountFilterFields(root: ParentNode): MountedFilter[];
}
let component: Promise<FilterModule> | undefined;
const mounted = new Set<MountedFilter>();

export async function initRepoFilters(root: ParentNode = document): Promise<void> {
  for (const field of mounted) {
    if (!field.element.isConnected) {
      field.destroy();
      mounted.delete(field);
    }
  }
  if (!root.querySelector("[data-stx-filter-field]")) return;
  const url = document.querySelector<HTMLElement>(".hub-main")?.dataset.sdkFilterModule;
  if (!url) throw new Error("Hub filter requires the installed SDK module URL");
  // The host template supplies the SDK's content-hashed static URL, never an
  // app query or user-controlled media path. The SDK owns markup and shortcuts.
  component ??= import(/* @vite-ignore */ url) as Promise<FilterModule>;
  const sdk = await component;
  if (root instanceof Element && !root.isConnected) return;
  for (const field of sdk.mountFilterFields(root)) mounted.add(field);
}
