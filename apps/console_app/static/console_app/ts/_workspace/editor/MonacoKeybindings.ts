/**
 * Monaco Keybinding Helpers
 * Emacs, Vim, and navigation keybindings for the Monaco editor
 */

/**
 * Add Emacs-style keybindings to a Monaco editor instance
 */
export function addEmacsKeybindings(editor: any, monaco: any): void {
  if (!editor) return;

  // Global event listener to prevent Chrome shortcuts
  const preventDefaultForEmacs = (e: KeyboardEvent) => {
    const activeElement = document.activeElement;
    const isInEditor =
      activeElement?.classList?.contains("inputarea") ||
      activeElement?.closest(".monaco-editor") !== null;

    if (!isInEditor) return;

    if (e.ctrlKey && !e.shiftKey && !e.altKey && !e.metaKey) {
      const key = e.key.toLowerCase();
      if (["n", "p", "w", "t", "y"].includes(key)) {
        console.log("[Emacs] Preventing default for Ctrl+" + key.toUpperCase());
        e.preventDefault();
      }
    }
  };

  document.addEventListener("keydown", preventDefaultForEmacs, true);
  (editor as any)._emacsPreventDefaultHandler = preventDefaultForEmacs;

  // Character navigation
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyF, () => {
    editor.trigger("keyboard", "cursorRight", {});
  });
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyB, () => {
    editor.trigger("keyboard", "cursorLeft", {});
  });
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyN, () => {
    editor.trigger("keyboard", "cursorDown", {});
  });
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyP, () => {
    editor.trigger("keyboard", "cursorUp", {});
  });

  // Alternative bindings (fallback for Chrome-blocked)
  editor.addCommand(monaco.KeyMod.Alt | monaco.KeyCode.KeyN, () => {
    editor.trigger("keyboard", "cursorDown", {});
  });
  editor.addCommand(monaco.KeyMod.Alt | monaco.KeyCode.KeyP, () => {
    editor.trigger("keyboard", "cursorUp", {});
  });

  // Word navigation
  editor.addCommand(monaco.KeyMod.Alt | monaco.KeyCode.KeyF, () => {
    editor.trigger("keyboard", "cursorWordRight", {});
  });
  editor.addCommand(monaco.KeyMod.Alt | monaco.KeyCode.KeyB, () => {
    editor.trigger("keyboard", "cursorWordLeft", {});
  });

  // Line beginning/end
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyA, () => {
    editor.trigger("keyboard", "cursorHome", {});
  });
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyE, () => {
    editor.trigger("keyboard", "cursorEnd", {});
  });

  console.log("[Emacs] Keybindings installed (abbreviated set)");
}

/**
 * Add global navigation keybindings that override Emacs/Vim modes
 * These shortcuts are ALWAYS prioritized for module navigation
 */
export function addGlobalNavigationKeybindings(editor: any, monaco: any): void {
  if (!editor) return;

  // Alt+Z: Toggle Zen Mode (dispatch event for zen-mode component)
  editor.addCommand(monaco.KeyMod.Alt | monaco.KeyCode.KeyZ, () => {
    console.log("[Monaco] Alt+Z - Toggle Zen Mode");
    const event = new KeyboardEvent("keydown", {
      key: "F11",
      keyCode: 122,
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(event);
  });

  // Alt+F: Toggle sidebar (Files panel)
  editor.addCommand(monaco.KeyMod.Alt | monaco.KeyCode.KeyF, () => {
    console.log("[Monaco] Alt+F - Toggle sidebar");
    const sidebarToggle = document.getElementById("sidebar-toggle");
    if (sidebarToggle) sidebarToggle.click();
  });

  // Alt+S: Scholar
  editor.addCommand(monaco.KeyMod.Alt | monaco.KeyCode.KeyS, () => {
    if (!window.location.pathname.startsWith("/apps/scholar/")) {
      console.log("[Monaco] Alt+S - Navigate to Scholar");
      window.location.href = "/apps/scholar/";
    }
  });

  // Alt+C: Code
  editor.addCommand(monaco.KeyMod.Alt | monaco.KeyCode.KeyC, () => {
    if (!window.location.pathname.startsWith("/apps/console/")) {
      console.log("[Monaco] Alt+C - Navigate to Code");
      window.location.href = "/apps/console/";
    }
  });

  // Alt+V: Vis
  editor.addCommand(monaco.KeyMod.Alt | monaco.KeyCode.KeyV, () => {
    if (!window.location.pathname.startsWith("/apps/vis/")) {
      console.log("[Monaco] Alt+V - Navigate to Vis");
      window.location.href = "/apps/vis/";
    }
  });

  // Alt+W: Writer
  editor.addCommand(monaco.KeyMod.Alt | monaco.KeyCode.KeyW, () => {
    if (!window.location.pathname.startsWith("/apps/writer/")) {
      console.log("[Monaco] Alt+W - Navigate to Writer");
      window.location.href = "/apps/writer/";
    }
  });

  console.log("[Monaco] Global navigation keybindings added (Alt+Z/F/S/C/V/W)");
}

/**
 * Add Ctrl+Enter keybinding for running code
 */
export function addRunCodeKeybinding(editor: any, monaco: any): void {
  if (!editor) return;

  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
    const runBtn = document.getElementById("btn-run") as HTMLButtonElement;
    if (runBtn && !runBtn.disabled) {
      console.log("[Keybinding] Ctrl+Enter pressed - triggering Run button");
      runBtn.click();
    } else if (runBtn?.disabled) {
      console.log("[Keybinding] Ctrl+Enter pressed but Run button is disabled");
    }
  });

  console.log("[Keybinding] Ctrl+Enter keybinding for Run added");
}

// EOF
