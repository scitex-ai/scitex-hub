/**
 * Monaco Editor Features Module
 * Handles Monaco-specific features: citations, drag-and-drop, protection, custom actions
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/monaco-editor/monaco-features.ts loaded",
);

/**
 * Setup Monaco Editor event listeners and actions
 */
export function setupMonacoEditorListeners(
  monacoEditor: any,
  monaco: any,
  onChangeCallback?: (content: string, wordCount: number) => void,
  currentSectionId?: string,
  saveCursorPositionFn?: (sectionId: string) => void,
  getOnChangeCallback?: () => ((content: string, wordCount: number) => void) | undefined
): void {
  if (!monacoEditor) return;

  // Track changes - use getter function if provided, otherwise fall back to direct callback
  monacoEditor.onDidChangeModelContent(() => {
    const content = monacoEditor.getValue();
    const wordCount = countWords(content);

    // Get callback at call time (allows late binding)
    const callback = getOnChangeCallback ? getOnChangeCallback() : onChangeCallback;
    if (callback) {
      callback(content, wordCount);
    }
  });

  // Save cursor position on cursor changes (debounced)
  let cursorSaveTimeout: number | undefined;
  monacoEditor.onDidChangeCursorPosition(() => {
    if (cursorSaveTimeout) {
      clearTimeout(cursorSaveTimeout);
    }
    cursorSaveTimeout = window.setTimeout(() => {
      if (currentSectionId && saveCursorPositionFn) {
        saveCursorPositionFn(currentSectionId);
      }
    }, 500); // Debounce by 500ms
  });

  // Add custom comment toggle action (Ctrl+/ or Cmd+/)
  monacoEditor.addAction({
    id: "toggle-line-comment",
    label: "Toggle Line Comment",
    keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.Slash],
    contextMenuGroupId: "modification",
    contextMenuOrder: 1.5,
    run: (editor: any) => {
      // Use Monaco's built-in toggle line comment action
      editor.trigger("keyboard", "editor.action.commentLine", {});
    },
  });

  // Add Ctrl+; (C-;) as alternative comment toggle shortcut
  monacoEditor.addAction({
    id: "toggle-line-comment-alt",
    label: "Toggle Line Comment (Alt)",
    keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.Semicolon],
    run: (editor: any) => {
      // Use Monaco's built-in toggle line comment action
      editor.trigger("keyboard", "editor.action.commentLine", {});
    },
  });

  console.log("[Editor] Monaco Editor listeners and actions configured");
}

/**
 * Count words in text
 */
function countWords(text: string): number {
  const trimmed = text.trim();
  if (!trimmed) return 0;
  return trimmed.split(/\s+/).length;
}

/**
 * Setup drag-and-drop zone for citation insertion
 */
export function setupCitationDropZone(monacoEditor: any): void {
  if (!monacoEditor) return;

  const editorDomNode = monacoEditor.getDomNode();
  if (!editorDomNode) return;

  // Dragover: Allow drop
  editorDomNode.addEventListener("dragover", (e: DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = "copy";
    }
    // Add visual feedback
    editorDomNode.parentElement?.classList.add("drag-over");
  });

  // Dragleave: Remove visual feedback
  editorDomNode.addEventListener("dragleave", () => {
    editorDomNode.parentElement?.classList.remove("drag-over");
  });

  // Drop: Insert citation or figure
  editorDomNode.addEventListener("drop", (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation(); // Prevent Monaco's default drop handling
    editorDomNode.parentElement?.classList.remove("drag-over");

    if (!e.dataTransfer) return;

    const droppedContent = e.dataTransfer.getData("text/plain");
    if (!droppedContent) return;

    // Get drop position from Monaco
    const position = monacoEditor.getTargetAtClientPoint(
      e.clientX,
      e.clientY,
    );
    if (!position) return;

    // Check if this is a figure (LaTeX code) or a citation key
    const isFigure = droppedContent.trim().startsWith("\\begin{figure}");

    let insertText: string;
    let messageType: string;
    let messageContent: string;

    if (isFigure) {
      // Insert figure LaTeX code as-is
      insertText = droppedContent;
      messageType = "figure";
      messageContent = "Figure inserted";
      console.log("[Editor] Inserting figure at drop position");
    } else {
      // Insert citation wrapped in \cite{}
      insertText = `\\cite{${droppedContent}}`;
      messageType = "citation";
      messageContent = `Citation added: ${droppedContent}`;
      console.log(`[Editor] Inserted citation at drop position: ${droppedContent}`);
    }

    const range = {
      startLineNumber: position.position.lineNumber,
      startColumn: position.position.column,
      endLineNumber: position.position.lineNumber,
      endColumn: position.position.column,
    };

    // Use pushEditOperations to prevent default text insertion
    monacoEditor.pushUndoStop();
    monacoEditor.executeEdits(`${messageType}-drop`, [
      {
        range: range,
        text: insertText,
        forceMoveMarkers: true,
      },
    ]);
    monacoEditor.pushUndoStop();

    // Focus editor and move cursor after inserted content
    monacoEditor.setPosition({
      lineNumber: position.position.lineNumber,
      column: position.position.column + insertText.length,
    });
    monacoEditor.focus();

    // Show toast notification
    const showToast = (window as any).showToast;
    if (showToast) {
      showToast(messageContent, "success");
    }
  });

  console.log("[Editor] Citation and figure drop zone configured");
}

/**
 * Setup citation protection - treat \cite{key} as atomic unit
 */
export function setupCitationProtection(monacoEditor: any, monaco: any): void {
  if (!monacoEditor) return;

  // Register link provider to detect citations
  monaco.languages.registerLinkProvider("latex", {
    provideLinks: (model: any) => {
      const links: any[] = [];
      const lineCount = model.getLineCount();

      for (let lineNumber = 1; lineNumber <= lineCount; lineNumber++) {
        const lineContent = model.getLineContent(lineNumber);

        // Find all \cite{...} patterns
        const regex = /\\cite[tp]?\{([^}]+)\}/g;
        let match;

        while ((match = regex.exec(lineContent)) !== null) {
          const startColumn = match.index + 1;
          const endColumn = match.index + match[0].length + 1;

          links.push({
            range: new monaco.Range(
              lineNumber,
              startColumn,
              lineNumber,
              endColumn,
            ),
            url: `#citation:${match[1]}`,
            tooltip: `Citation: ${match[1]} (Click to select whole citation)`,
          });
        }
      }

      return { links };
    },
  });
}

/**
 * Force suggestion widget to show details panel on right side
 */
export function setupSuggestionWidgetObserver(monacoEditor: any): void {
  // Force details panel to always show
  setTimeout(() => {
    const suggestController = (monacoEditor as any)._contentWidget
      ?._widget;
    if (suggestController && suggestController.widget) {
      suggestController.widget._setDetailsVisible(true);
    }
  }, 1000);

  // Watch for suggestion widget creation and force positioning + auto-expand
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node: any) => {
        if (
          node.classList &&
          node.classList.contains("suggest-widget")
        ) {
          console.log(
            "[Citations] Suggestion widget detected, forcing right-side layout and auto-expanding details",
          );

          // Force horizontal layout
          node.style.flexDirection = "row";
          node.style.alignItems = "flex-start";

          // Find and reposition details panel
          const details = node.querySelector(".suggest-details");
          if (details) {
            (details as HTMLElement).style.position = "relative";
            (details as HTMLElement).style.order = "2";
            (details as HTMLElement).style.marginLeft = "4px";
            (details as HTMLElement).style.display = "block";
            (details as HTMLElement).style.visibility = "visible";
          }

          // Programmatically trigger "show more" mode
          setTimeout(() => {
            try {
              // Try to access Monaco's suggest controller
              if (monacoEditor) {
                // Trigger suggest widget to show details
                monacoEditor.trigger(
                  "keyboard",
                  "toggleSuggestionDetails",
                  {},
                );
              }
            } catch (e) {
              console.log(
                "[Citations] Could not auto-trigger details:",
                e,
              );
            }
          }, 50);
        }
      });
    });
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
}
