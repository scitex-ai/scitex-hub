/**
 * Editor Configuration Module
 * Manages editor configuration (theme, read-only, keybindings)
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/monaco-editor/editor-config.ts loaded",
);

export class EditorConfig {
  private editor: any;
  private monacoEditor: any;
  private editorType: "monaco" | "codemirror";

  constructor(
    editor: any,
    monacoEditor: any,
    editorType: "monaco" | "codemirror"
  ) {
    this.editor = editor;
    this.monacoEditor = monacoEditor;
    this.editorType = editorType;
  }

  /**
   * Set editor theme
   */
  setTheme(theme: string): void {
    if (this.editorType === "monaco" && this.monacoEditor) {
      console.log("[Editor] Setting Monaco theme to:", theme);
      // Map common CodeMirror theme names to Monaco themes
      const monacoThemeMap: Record<string, string> = {
        zenburn: "vs-dark",
        monokai: "vs-dark",
        dracula: "vs-dark",
        eclipse: "vs",
        neat: "vs",
        "solarized light": "vs",
        "scitex-dark": "scitex-dark",
        default: "vs",
      };
      const monacoTheme = monacoThemeMap[theme.toLowerCase()] || "scitex-dark";
      (window as any).monaco.editor.setTheme(monacoTheme);
    } else {
      // CodeMirror theme change
      console.log("[Editor] Setting CodeMirror theme to:", theme);
      const cmEditor = (document.querySelector(".CodeMirror") as any)
        ?.CodeMirror;
      if (cmEditor) {
        cmEditor.setOption("theme", theme);
      }
    }
  }

  /**
   * Set editor read-only state
   */
  setReadOnly(readOnly: boolean): void {
    if (this.editorType === "monaco" && this.monacoEditor) {
      console.log("[Editor] Setting Monaco readOnly to:", readOnly);
      this.monacoEditor.updateOptions({ readOnly: readOnly });
    } else {
      // CodeMirror read-only mode
      console.log("[Editor] Setting CodeMirror readOnly to:", readOnly);
      const cmEditor = (document.querySelector(".CodeMirror") as any)
        ?.CodeMirror;
      if (cmEditor) {
        cmEditor.setOption("readOnly", readOnly);
      }
    }
  }

  /**
   * Set editor keybinding mode
   */
  setKeyBinding(mode: string): void {
    if (this.editorType === "monaco" && this.monacoEditor) {
      console.log("[Editor] Monaco keybinding change requested:", mode);
      // Monaco doesn't directly support Vim/Emacs keybindings without extensions
      // For now, just log - would need monaco-vim or monaco-emacs packages
      console.warn(
        "[Editor] Monaco Vim/Emacs keybindings require additional packages",
      );
    } else {
      // CodeMirror keymap
      console.log("[Editor] Setting CodeMirror keymap to:", mode);
      const cmEditor = (document.querySelector(".CodeMirror") as any)
        ?.CodeMirror;
      if (cmEditor) {
        cmEditor.setOption("keyMap", mode);
      }
    }
  }
}
