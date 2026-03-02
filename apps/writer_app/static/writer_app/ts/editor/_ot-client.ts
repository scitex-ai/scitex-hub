/**
 * Operational Transform Client
 *
 * Handles client-side operational transforms for conflict-free collaborative editing
 * Based on the OT algorithm from operational_transform_service.py
 */

console.log("[DEBUG] ot-client.ts loaded");

/**
 * Operation types
 */
enum OpType {
  RETAIN = "retain",
  INSERT = "insert",
  DELETE = "delete",
}

/**
 * Single operation
 */
interface Operation {
  type: OpType;
  chars?: string; // For INSERT/DELETE
  count?: number; // For RETAIN/DELETE
}

/**
 * Text operation composed of multiple operations
 */
export class TextOperation {
  ops: Operation[] = [];

  retain(count: number): TextOperation {
    if (count > 0) {
      this.ops.push({ type: OpType.RETAIN, count });
    }
    return this;
  }

  insert(text: string): TextOperation {
    if (text) {
      this.ops.push({ type: OpType.INSERT, chars: text });
    }
    return this;
  }

  delete(count: number): TextOperation {
    if (count > 0) {
      this.ops.push({ type: OpType.DELETE, count });
    }
    return this;
  }

  /**
   * Apply operation to text
   */
  apply(text: string): string {
    const result: string[] = [];
    let pos = 0;

    for (const op of this.ops) {
      if (op.type === OpType.RETAIN && op.count) {
        result.push(text.substring(pos, pos + op.count));
        pos += op.count;
      } else if (op.type === OpType.INSERT && op.chars) {
        result.push(op.chars);
      } else if (op.type === OpType.DELETE && op.count) {
        pos += op.count;
      }
    }

    return result.join("");
  }

  /**
   * Convert to JSON for transmission
   */
  toJSON(): { ops: Operation[] } {
    return { ops: this.ops };
  }

  /**
   * Create from JSON
   */
  static fromJSON(data: { ops: Operation[] }): TextOperation {
    const op = new TextOperation();
    op.ops = data.ops || [];
    return op;
  }

  /**
   * Create operation from text diff
   */
  static fromDiff(oldText: string, newText: string): TextOperation {
    const op = new TextOperation();

    // Simple diff algorithm
    let i = 0;
    let j = 0;

    // Find common prefix
    while (i < oldText.length && i < newText.length && oldText[i] === newText[i]) {
      i++;
    }

    if (i > 0) {
      op.retain(i);
    }

    // Find common suffix
    let oldEnd = oldText.length;
    let newEnd = newText.length;

    while (
      oldEnd > i &&
      newEnd > i &&
      oldText[oldEnd - 1] === newText[newEnd - 1]
    ) {
      oldEnd--;
      newEnd--;
    }

    // Handle deletions
    if (oldEnd > i) {
      op.delete(oldEnd - i);
    }

    // Handle insertions
    if (newEnd > i) {
      op.insert(newText.substring(i, newEnd));
    }

    // Retain suffix
    if (oldEnd < oldText.length) {
      op.retain(oldText.length - oldEnd);
    }

    return op;
  }
}

/**
 * OT Client - manages document versions and operation buffering
 */
export class OTClient {
  private sectionVersions: Map<string, number> = new Map();
  private sectionTexts: Map<string, string> = new Map();
  private pendingOperations: Map<string, TextOperation[]> = new Map();

  /**
   * Initialize section
   */
  initSection(sectionId: string, initialText: string, version: number = 0): void {
    this.sectionVersions.set(sectionId, version);
    this.sectionTexts.set(sectionId, initialText);
    this.pendingOperations.set(sectionId, []);

    console.log(`[OTClient] Initialized section ${sectionId} at version ${version}`);
  }

  /**
   * Get current version for a section
   */
  getVersion(sectionId: string): number {
    return this.sectionVersions.get(sectionId) || 0;
  }

  /**
   * Get current text for a section
   */
  getText(sectionId: string): string {
    return this.sectionTexts.get(sectionId) || "";
  }

  /**
   * Apply local text change
   */
  applyLocalChange(sectionId: string, newText: string): TextOperation | null {
    const oldText = this.getText(sectionId);

    if (oldText === newText) {
      return null; // No change
    }

    // Create operation from diff
    const operation = TextOperation.fromDiff(oldText, newText);

    // Update local text
    this.sectionTexts.set(sectionId, newText);

    // Buffer operation
    const pending = this.pendingOperations.get(sectionId) || [];
    pending.push(operation);
    this.pendingOperations.set(sectionId, pending);

    console.log(`[OTClient] Local change in ${sectionId}, ${operation.ops.length} ops`);

    return operation;
  }

  /**
   * Apply remote operation
   */
  applyRemoteOperation(
    sectionId: string,
    operation: TextOperation,
    serverVersion: number
  ): boolean {
    const currentVersion = this.getVersion(sectionId);
    const currentText = this.getText(sectionId);

    console.log(
      `[OTClient] Applying remote op for ${sectionId}, server v${serverVersion}, client v${currentVersion}`
    );

    // Transform against pending operations
    const pending = this.pendingOperations.get(sectionId) || [];
    let transformedOp = operation;

    for (const pendingOp of pending) {
      // Transform remote operation against pending local operation
      transformedOp = this.transform(transformedOp, pendingOp, "left");
    }

    // Apply transformed operation
    try {
      const newText = transformedOp.apply(currentText);
      this.sectionTexts.set(sectionId, newText);
      this.sectionVersions.set(sectionId, serverVersion);

      console.log(`[OTClient] Applied remote op, new version ${serverVersion}`);
      return true;
    } catch (error) {
      console.error(`[OTClient] Error applying operation:`, error);
      return false;
    }
  }

  /**
   * Acknowledge operation sent to server
   */
  acknowledgeOperation(sectionId: string, serverVersion: number): void {
    // Remove first pending operation
    const pending = this.pendingOperations.get(sectionId) || [];
    if (pending.length > 0) {
      pending.shift();
      this.pendingOperations.set(sectionId, pending);
    }

    // Update version
    this.sectionVersions.set(sectionId, serverVersion);

    console.log(`[OTClient] Acknowledged op for ${sectionId}, v${serverVersion}`);
  }

  /**
   * Transform two operations (simplified implementation)
   */
  private transform(
    op1: TextOperation,
    op2: TextOperation,
    side: "left" | "right"
  ): TextOperation {
    // This is a simplified version
    // Production would need full OT transformation algorithm
    const result = new TextOperation();

    let i1 = 0;
    let i2 = 0;

    while (i1 < op1.ops.length || i2 < op2.ops.length) {
      const o1 = op1.ops[i1];
      const o2 = op2.ops[i2];

      if (!o1 && !o2) break;

      // Both insert
      if (o1?.type === OpType.INSERT && o2?.type === OpType.INSERT) {
        if (side === "left") {
          result.insert(o1.chars!);
          result.retain(o2.chars!.length);
          i1++;
        } else {
          result.retain(o2.chars!.length);
          i2++;
        }
      }
      // op1 insert
      else if (o1?.type === OpType.INSERT) {
        result.insert(o1.chars!);
        i1++;
      }
      // op2 insert
      else if (o2?.type === OpType.INSERT) {
        result.retain(o2.chars!.length);
        i2++;
      }
      // Both retain or delete
      else {
        if (o1?.type === OpType.RETAIN && o2?.type === OpType.RETAIN) {
          const min = Math.min(o1.count!, o2.count!);
          result.retain(min);

          if (o1.count === min) i1++;
          if (o2.count === min) i2++;
        } else if (o1?.type === OpType.DELETE && o2?.type === OpType.DELETE) {
          const min = Math.min(o1.count!, o2.count!);

          if (o1.count === min) i1++;
          if (o2.count === min) i2++;
        } else {
          i1++;
          i2++;
        }
      }
    }

    return result;
  }

  /**
   * Get pending operations count
   */
  getPendingCount(sectionId: string): number {
    return (this.pendingOperations.get(sectionId) || []).length;
  }
}

// Export for global access
declare global {
  interface Window {
    OTClient: typeof OTClient;
    TextOperation: typeof TextOperation;
  }
}

window.OTClient = OTClient;
window.TextOperation = TextOperation;
