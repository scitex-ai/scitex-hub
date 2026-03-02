/**
 * Operational Transform (OT) Operations Library
 * Based on ShareJS and Overleaf algorithms
 * Client-side implementation to match backend OT coordinator
 *
 * @version 1.0.0
 * @author SciTeX Development Team
 */

console.log("[DEBUG] OT Operations library loaded");

// ============================================================================
// OT Operation Types
// ============================================================================

export enum OperationType {
  RETAIN = 'retain',
  INSERT = 'insert',
  DELETE = 'delete'
}

export interface Operation {
  type: OperationType;
  chars?: number;
  text?: string;
}

// ============================================================================
// TextOperation Class
// ============================================================================

export class TextOperation {
  ops: Operation[] = [];
  baseLength: number = 0;
  targetLength: number = 0;

  /**
   * Check if this operation doesn't do anything
   */
  isNoop(): boolean {
    return this.ops.length === 0 ||
      (this.ops.length === 1 &&
        this.ops[0].type === OperationType.RETAIN);
  }

  /**
   * Retain n characters
   */
  retain(n: number): TextOperation {
    if (n === 0) return this;

    this.baseLength += n;
    this.targetLength += n;

    const lastOp = this.ops[this.ops.length - 1];
    if (lastOp && lastOp.type === OperationType.RETAIN) {
      lastOp.chars = (lastOp.chars || 0) + n;
    } else {
      this.ops.push({ type: OperationType.RETAIN, chars: n });
    }

    return this;
  }

  /**
   * Insert a string
   */
  insert(str: string): TextOperation {
    if (str.length === 0) return this;

    this.targetLength += str.length;

    const lastOp = this.ops[this.ops.length - 1];
    if (lastOp && lastOp.type === OperationType.INSERT) {
      lastOp.text = (lastOp.text || '') + str;
    } else if (lastOp && lastOp.type === OperationType.DELETE) {
      // Insert goes before delete
      if (this.ops.length > 1) {
        const secondToLast = this.ops[this.ops.length - 2];
        if (secondToLast && secondToLast.type === OperationType.INSERT) {
          secondToLast.text = (secondToLast.text || '') + str;
        } else {
          this.ops.splice(this.ops.length - 1, 0, {
            type: OperationType.INSERT,
            text: str
          });
        }
      } else {
        this.ops.unshift({ type: OperationType.INSERT, text: str });
      }
    } else {
      this.ops.push({ type: OperationType.INSERT, text: str });
    }

    return this;
  }

  /**
   * Delete n characters
   */
  delete(n: number | string): TextOperation {
    const length = typeof n === 'string' ? n.length : n;
    if (length === 0) return this;

    this.baseLength += length;

    const lastOp = this.ops[this.ops.length - 1];
    if (lastOp && lastOp.type === OperationType.DELETE) {
      lastOp.chars = (lastOp.chars || 0) + length;
    } else {
      this.ops.push({ type: OperationType.DELETE, chars: length });
    }

    return this;
  }

  /**
   * Apply this operation to a string
   */
  apply(str: string): string {
    if (str.length !== this.baseLength) {
      throw new Error(
        `The operation's base length must be equal to the string's length. ` +
        `Expected ${this.baseLength}, got ${str.length}`
      );
    }

    let result = '';
    let strIndex = 0;

    for (const op of this.ops) {
      switch (op.type) {
        case OperationType.RETAIN:
          if (strIndex + (op.chars || 0) > str.length) {
            throw new Error('Operation cannot retain more chars than are left in string');
          }
          result += str.slice(strIndex, strIndex + (op.chars || 0));
          strIndex += op.chars || 0;
          break;

        case OperationType.INSERT:
          result += op.text || '';
          break;

        case OperationType.DELETE:
          strIndex += op.chars || 0;
          break;
      }
    }

    if (strIndex !== str.length) {
      throw new Error('The operation did not operate on the whole string');
    }

    if (result.length !== this.targetLength) {
      throw new Error(`Result length mismatch. Expected ${this.targetLength}, got ${result.length}`);
    }

    return result;
  }

  /**
   * Compose this operation with another operation
   * Returns a new operation that has the same effect as applying this followed by other
   */
  compose(other: TextOperation): TextOperation {
    if (this.targetLength !== other.baseLength) {
      throw new Error('The base length of the second operation must be equal to the target length of the first operation');
    }

    const operation = new TextOperation();
    const ops1 = this.ops.slice();
    const ops2 = other.ops.slice();

    let i1 = 0, i2 = 0;
    let op1 = ops1[i1++];
    let op2 = ops2[i2++];

    while (op1 || op2) {
      // Insert from op2
      if (op2 && op2.type === OperationType.INSERT) {
        operation.insert(op2.text || '');
        op2 = ops2[i2++];
        continue;
      }

      // Delete from op1
      if (op1 && op1.type === OperationType.DELETE) {
        operation.delete(op1.chars || 0);
        op1 = ops1[i1++];
        continue;
      }

      if (!op1 || !op2) {
        throw new Error('Cannot compose operations: operations do not match');
      }

      // Both are retains or op1 is insert
      if (op1.type === OperationType.RETAIN && op2.type === OperationType.RETAIN) {
        const chars1 = op1.chars || 0;
        const chars2 = op2.chars || 0;

        if (chars1 > chars2) {
          operation.retain(chars2);
          op1 = { type: OperationType.RETAIN, chars: chars1 - chars2 };
          op2 = ops2[i2++];
        } else if (chars1 === chars2) {
          operation.retain(chars1);
          op1 = ops1[i1++];
          op2 = ops2[i2++];
        } else {
          operation.retain(chars1);
          op2 = { type: OperationType.RETAIN, chars: chars2 - chars1 };
          op1 = ops1[i1++];
        }
      } else if (op1.type === OperationType.INSERT && op2.type === OperationType.RETAIN) {
        const text = op1.text || '';
        const chars2 = op2.chars || 0;

        if (text.length > chars2) {
          operation.insert(text.slice(0, chars2));
          op1 = { type: OperationType.INSERT, text: text.slice(chars2) };
          op2 = ops2[i2++];
        } else if (text.length === chars2) {
          operation.insert(text);
          op1 = ops1[i1++];
          op2 = ops2[i2++];
        } else {
          operation.insert(text);
          op2 = { type: OperationType.RETAIN, chars: chars2 - text.length };
          op1 = ops1[i1++];
        }
      } else if (op1.type === OperationType.INSERT && op2.type === OperationType.DELETE) {
        const text = op1.text || '';
        const chars2 = op2.chars || 0;

        if (text.length > chars2) {
          op1 = { type: OperationType.INSERT, text: text.slice(chars2) };
          op2 = ops2[i2++];
        } else if (text.length === chars2) {
          op1 = ops1[i1++];
          op2 = ops2[i2++];
        } else {
          op2 = { type: OperationType.DELETE, chars: chars2 - text.length };
          op1 = ops1[i1++];
        }
      } else if (op1.type === OperationType.RETAIN && op2.type === OperationType.DELETE) {
        const chars1 = op1.chars || 0;
        const chars2 = op2.chars || 0;

        if (chars1 > chars2) {
          operation.delete(chars2);
          op1 = { type: OperationType.RETAIN, chars: chars1 - chars2 };
          op2 = ops2[i2++];
        } else if (chars1 === chars2) {
          operation.delete(chars1);
          op1 = ops1[i1++];
          op2 = ops2[i2++];
        } else {
          operation.delete(chars1);
          op2 = { type: OperationType.DELETE, chars: chars2 - chars1 };
          op1 = ops1[i1++];
        }
      }
    }

    return operation;
  }

  /**
   * Serialize to JSON for sending to server
   */
  toJSON(): { ops: Operation[], baseLength: number, targetLength: number } {
    return {
      ops: this.ops,
      baseLength: this.baseLength,
      targetLength: this.targetLength
    };
  }

  /**
   * Create from JSON received from server
   */
  static fromJSON(json: { ops: Operation[], baseLength: number, targetLength: number }): TextOperation {
    const op = new TextOperation();
    op.ops = json.ops;
    op.baseLength = json.baseLength;
    op.targetLength = json.targetLength;
    return op;
  }

  /**
   * Convert to string for debugging
   */
  toString(): string {
    return this.ops.map(op => {
      switch (op.type) {
        case OperationType.RETAIN: return `retain(${op.chars})`;
        case OperationType.INSERT: return `insert("${op.text}")`;
        case OperationType.DELETE: return `delete(${op.chars})`;
      }
    }).join(', ');
  }
}

// ============================================================================
// OT Transform Function
// ============================================================================

/**
 * Transform two operations A and B that happened concurrently
 * Returns [A', B'] such that apply(apply(S, A), B') = apply(apply(S, B), A')
 *
 * @param op1 First operation
 * @param op2 Second operation
 * @param _side 'left' or 'right' - determines priority in case of conflicts (unused but kept for API compatibility)
 * @returns Tuple of transformed operations [op1', op2']
 */
export function transform(op1: TextOperation, op2: TextOperation, _side: 'left' | 'right' = 'left'): [TextOperation, TextOperation] {
  if (op1.baseLength !== op2.baseLength) {
    throw new Error('Both operations must have the same base length');
  }

  const op1Prime = new TextOperation();
  const op2Prime = new TextOperation();

  const ops1 = op1.ops.slice();
  const ops2 = op2.ops.slice();

  let i1 = 0, i2 = 0;
  let op1Current = ops1[i1++];
  let op2Current = ops2[i2++];

  while (op1Current || op2Current) {
    // Handle insert operations
    if (op1Current && op1Current.type === OperationType.INSERT) {
      op1Prime.insert(op1Current.text || '');
      op2Prime.retain((op1Current.text || '').length);
      op1Current = ops1[i1++];
      continue;
    }

    if (op2Current && op2Current.type === OperationType.INSERT) {
      op1Prime.retain((op2Current.text || '').length);
      op2Prime.insert(op2Current.text || '');
      op2Current = ops2[i2++];
      continue;
    }

    if (!op1Current || !op2Current) {
      throw new Error('Cannot transform operations: operations do not match');
    }

    let minLength: number;

    if (op1Current.type === OperationType.RETAIN && op2Current.type === OperationType.RETAIN) {
      const chars1 = op1Current.chars || 0;
      const chars2 = op2Current.chars || 0;

      if (chars1 > chars2) {
        minLength = chars2;
        op1Current = { type: OperationType.RETAIN, chars: chars1 - chars2 };
        op2Current = ops2[i2++];
      } else if (chars1 === chars2) {
        minLength = chars2;
        op1Current = ops1[i1++];
        op2Current = ops2[i2++];
      } else {
        minLength = chars1;
        op2Current = { type: OperationType.RETAIN, chars: chars2 - chars1 };
        op1Current = ops1[i1++];
      }

      op1Prime.retain(minLength);
      op2Prime.retain(minLength);
    } else if (op1Current.type === OperationType.DELETE && op2Current.type === OperationType.DELETE) {
      const chars1 = op1Current.chars || 0;
      const chars2 = op2Current.chars || 0;

      if (chars1 > chars2) {
        op1Current = { type: OperationType.DELETE, chars: chars1 - chars2 };
        op2Current = ops2[i2++];
      } else if (chars1 === chars2) {
        op1Current = ops1[i1++];
        op2Current = ops2[i2++];
      } else {
        op2Current = { type: OperationType.DELETE, chars: chars2 - chars1 };
        op1Current = ops1[i1++];
      }
    } else if (op1Current.type === OperationType.DELETE && op2Current.type === OperationType.RETAIN) {
      const chars1 = op1Current.chars || 0;
      const chars2 = op2Current.chars || 0;

      if (chars1 > chars2) {
        minLength = chars2;
        op1Current = { type: OperationType.DELETE, chars: chars1 - chars2 };
        op2Current = ops2[i2++];
      } else if (chars1 === chars2) {
        minLength = chars1;
        op1Current = ops1[i1++];
        op2Current = ops2[i2++];
      } else {
        minLength = chars1;
        op2Current = { type: OperationType.RETAIN, chars: chars2 - chars1 };
        op1Current = ops1[i1++];
      }

      op1Prime.delete(minLength);
    } else if (op1Current.type === OperationType.RETAIN && op2Current.type === OperationType.DELETE) {
      const chars1 = op1Current.chars || 0;
      const chars2 = op2Current.chars || 0;

      if (chars1 > chars2) {
        minLength = chars2;
        op1Current = { type: OperationType.RETAIN, chars: chars1 - chars2 };
        op2Current = ops2[i2++];
      } else if (chars1 === chars2) {
        minLength = chars2;
        op1Current = ops1[i1++];
        op2Current = ops2[i2++];
      } else {
        minLength = chars1;
        op2Current = { type: OperationType.DELETE, chars: chars2 - chars1 };
        op1Current = ops1[i1++];
      }

      op2Prime.delete(minLength);
    }
  }

  return [op1Prime, op2Prime];
}
