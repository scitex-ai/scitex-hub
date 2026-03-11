/**
 * Inline Input Helper for WorkspaceFilesTree
 * Handles DOM creation of inline file/folder name inputs used during creation.
 */

export type InlineInputType = "file" | "directory";

export interface InlineInputOptions {
  /** Parent container to insert the input row into */
  container: HTMLElement;
  /** Where to insert — "after" a reference sibling, or "prepend" as first child */
  insertMode: "after-sibling" | "prepend";
  /** Used only when insertMode is "after-sibling" */
  sibling?: HTMLElement;
  type: InlineInputType;
  /** Called with the trimmed name when the user confirms; empty string means cancel */
  onSubmit: (name: string) => Promise<void>;
}

/**
 * Build and attach an inline text input row for naming a new file or folder.
 * Removes itself from the DOM after submission or cancellation.
 */
export function attachInlineInput(options: InlineInputOptions): void {
  const { container, insertMode, sibling, type, onSubmit } = options;

  const inputRow = document.createElement("div");
  inputRow.className = `wft-item wft-${type} wft-inline-create`;

  const iconClass =
    type === "file"
      ? "fas fa-file wft-inline-create-icon-file"
      : "fas fa-folder wft-inline-create-icon-folder";

  const placeholder = type === "file" ? "filename.ext" : "folder name";

  inputRow.innerHTML = `
    <span class="wft-spacer"></span>
    <span class="wft-icon"><i class="${iconClass}"></i></span>
    <input type="text" class="wft-inline-input" placeholder="${placeholder}" />
  `;

  if (insertMode === "after-sibling" && sibling) {
    sibling.after(inputRow);
  } else {
    container.insertBefore(inputRow, container.firstChild);
  }

  const input = inputRow.querySelector(".wft-inline-input") as HTMLInputElement;
  if (!input) {
    inputRow.remove();
    return;
  }

  input.focus();

  let submitted = false;

  const cleanup = (): void => {
    inputRow.remove();
  };

  const submit = async (): Promise<void> => {
    if (submitted) return;
    submitted = true;

    const name = input.value.trim();
    if (!name) {
      cleanup();
      return;
    }

    await onSubmit(name);
    cleanup();
  };

  input.addEventListener("blur", () => {
    // Small delay to allow click events to fire first
    setTimeout(() => submit(), 100);
  });

  input.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      input.blur();
    } else if (e.key === "Escape") {
      e.preventDefault();
      cleanup();
    }
  });
}
