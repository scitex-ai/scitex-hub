/**
 * Editor main page functionality
 * Corresponds to: templates/writer_app/editor/editor.html
 */

class EditorPage {
  private _editor: any;
  private _pdfPreview: HTMLElement | null;

  constructor() {
    this._pdfPreview = document.getElementById("pdf-preview");
    this.init();
  }

  private init(): void {
    console.log("[Editor] Initializing editor page");
    this.setupEditor();
  }

  private setupEditor(): void {
    console.log("[Editor] Setting up Monaco editor");
  }

  public compile(): void {
    console.log("[Editor] Starting compilation");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new EditorPage();
});
