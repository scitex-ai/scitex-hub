/**
 * Synchronization Operations for Writer Collaboration
 * Handles conversion between Monaco editor changes and OT operations
 *
 * @version 1.0.0
 * @author SciTeX Development Team
 */

import { TextOperation } from '../ot/operations.ts';

declare global {
  interface Window {
    monacoEditors?: Map<string, any>;
  }
}

/**
 * Convert Monaco editor change to OT operation
 */
export function monacoChangeToOTOperation(change: any, editor: any): TextOperation {
  const operation = new TextOperation();
  const model = editor.getModel();
  const fullText = model.getValue();

  // Calculate position before change
  const startOffset = model.getOffsetAt(change.range.getStartPosition());
  const endOffset = model.getOffsetAt(change.range.getEndPosition());

  // Retain characters before change
  if (startOffset > 0) {
    operation.retain(startOffset);
  }

  // Delete old text if any
  const deletedLength = endOffset - startOffset;
  if (deletedLength > 0) {
    operation.delete(deletedLength);
  }

  // Insert new text if any
  if (change.text.length > 0) {
    operation.insert(change.text);
  }

  // Retain characters after change
  const remainingLength = fullText.length - startOffset - change.text.length;
  if (remainingLength > 0) {
    operation.retain(remainingLength);
  }

  return operation;
}

/**
 * Apply remote OT operation to Monaco editor
 */
export function applyRemoteOperation(
  section: string,
  operation: TextOperation,
  changeListeners: Map<string, any>
): void {
  if (!window.monacoEditors) {
    return;
  }

  const editor = window.monacoEditors.get(section);
  if (!editor) {
    console.warn(`[Sync] Editor not found for section: ${section}`);
    return;
  }

  const model = editor.getModel();
  const currentText = model.getValue();

  // Suppress our own change listeners while applying remote operation
  const changeListener = changeListeners.get(section);
  if (changeListener) {
    changeListener.dispose();
  }

  try {
    // Apply operation to text
    const newText = operation.apply(currentText);

    // Update editor
    model.setValue(newText);
  } catch (error) {
    console.error('[Sync] Failed to apply remote operation:', error);
  } finally {
    // Re-enable change listener
    const newListener = editor.onDidChangeModelContent((event: any) => {
      // Note: The handler needs to be re-registered by the manager
      console.warn('[Sync] Change listener needs re-registration');
    });
    changeListeners.set(section, newListener);
  }
}

/**
 * Send cursor position to server
 */
export function sendCurrentCursorPosition(
  section: string,
  editor: any,
  wsClient: any
): void {
  if (!wsClient || !editor) {
    return;
  }

  const position = editor.getPosition();
  const model = editor.getModel();
  const offset = model.getOffsetAt(position);

  wsClient.sendCursorPosition({
    section: section,
    position: offset,
    lineNumber: position.lineNumber,
    column: position.column
  });
}
