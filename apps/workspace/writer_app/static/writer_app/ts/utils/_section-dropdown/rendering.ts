/** DOM-only rendering for the writer section dropdown. */

function encodePath(path: string): string {
  return path.split("/").map(encodeURIComponent).join("/");
}

function generateFilePath(section: any, docType: string): string {
  const username = String(
    (window as any).WRITER_CONFIG?.projectOwner || "ywatanabe",
  );
  const projectSlug = String(
    (window as any).WRITER_CONFIG?.projectSlug || "default-project",
  );
  let sectionPath: string;
  if (section.path) {
    sectionPath = String(section.path);
  } else {
    const name = String(section.id).replace(`${docType}/`, "");
    const docDirMap: Record<string, string> = {
      manuscript: "01_manuscript",
      supplementary: "02_supplementary",
      revision: "03_revision",
    };
    sectionPath = `${docDirMap[docType] || `01_${docType}`}/contents/${name}.tex`;
  }
  return `/${encodeURIComponent(username)}/${encodeURIComponent(projectSlug)}/blob/scitex/writer/${encodePath(sectionPath)}`;
}

function icon(className: string): HTMLElement {
  const element = document.createElement("i");
  element.className = className;
  return element;
}

function actionButton(
  action: string,
  title: string,
  iconClass: string,
): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn btn-xs btn-outline-secondary";
  button.dataset.action = action;
  button.title = title;
  button.appendChild(icon(iconClass));
  button.addEventListener("click", (event) => event.stopPropagation());
  return button;
}

function renderSectionItem(
  section: any,
  index: number,
  docType: string,
): HTMLElement {
  const isExcluded = section.excluded === true;
  const isOptional = section.optional === true;
  const isViewOnly = section.view_only === true;
  const isCompiledPdf = section.name === "compiled_pdf";
  const label = String(section.label ?? "");

  const item = document.createElement("div");
  item.className = `section-item${isExcluded ? " excluded" : ""} section-item-with-actions`;
  item.dataset.sectionId = String(section.id ?? "");
  item.dataset.index = String(index);
  item.dataset.optional = String(isOptional);
  item.draggable = !isCompiledPdf;
  item.title = `${isCompiledPdf ? "View" : "Switch to"} ${label}`;

  const drag = document.createElement("span");
  drag.className = "section-drag-handle";
  drag.title = "Drag to reorder";
  drag.textContent = "⋮⋮";
  if (isCompiledPdf) drag.style.visibility = "hidden";
  item.appendChild(drag);

  if (!isCompiledPdf) {
    const page = document.createElement("span");
    page.className = "section-page-number";
    page.style.cssText =
      "color: var(--color-fg-muted); font-size: 0.75rem; min-width: 20px;";
    page.textContent = String(index + 1);
    item.appendChild(page);
  }

  const name = document.createElement("span");
  name.className = "section-item-name";
  name.textContent = label;
  item.appendChild(name);

  if (!isViewOnly && (isOptional || isExcluded)) {
    const toggle = document.createElement("label");
    toggle.className = "ios-toggle";
    toggle.dataset.action = "toggle-visibility";
    toggle.title = isExcluded
      ? "Include in compilation"
      : "Exclude from compilation";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = !isExcluded;
    const slider = document.createElement("span");
    slider.className = "ios-toggle-slider";
    toggle.append(input, slider);
    item.appendChild(toggle);
  }

  const actions = document.createElement("div");
  actions.className = "section-item-actions";
  if (isCompiledPdf) {
    actions.appendChild(
      actionButton("compile-full", `Compile ${label} PDF`, "fas fa-file-pdf"),
    );
  }
  const link = document.createElement("a");
  link.className = "btn btn-xs btn-outline-secondary";
  link.href = generateFilePath(section, docType);
  link.title = `Go to ${label} file`;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.appendChild(icon("fas fa-folder-open"));
  link.addEventListener("click", (event) => event.stopPropagation());
  actions.appendChild(link);
  actions.appendChild(
    actionButton(
      "download-section",
      `Download ${label} PDF`,
      "fas fa-download",
    ),
  );
  item.appendChild(actions);
  return item;
}

export function renderSectionDropdown(
  sections: any[],
  docType: string,
): DocumentFragment {
  const fragment = document.createDocumentFragment();
  const regular = document.createElement("div");
  regular.className = "section-items-scrollable";
  const footer = document.createElement("div");
  footer.className = "section-items-footer";
  const firstDivider = document.createElement("div");
  firstDivider.className = "section-divider";
  footer.appendChild(firstDivider);

  sections.forEach((section, index) => {
    const item = renderSectionItem(section, index, docType);
    (section.name === "compiled_pdf" ? footer : regular).appendChild(item);
  });

  const secondDivider = document.createElement("div");
  secondDivider.className = "section-divider";
  footer.appendChild(secondDivider);
  const add = document.createElement("div");
  add.className = "section-action-item";
  add.dataset.action = "new-section";
  add.append(icon("fas fa-plus"));
  const text = document.createElement("span");
  text.textContent = "Add New Section";
  add.appendChild(text);
  footer.appendChild(add);
  fragment.append(regular, footer);
  return fragment;
}
