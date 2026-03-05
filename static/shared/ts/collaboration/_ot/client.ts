/**
 * OT Client
 * Manages local operations, synchronization with server, and transformation
 *
 * State machine:
 * - Synchronized: No pending operations
 * - AwaitingConfirm: One operation sent, waiting for acknowledgment
 * - AwaitingWithBuffer: One operation sent, one buffered locally
 *
 * @version 1.0.0
 * @author SciTeX Development Team
 */

import { TextOperation, transform } from './operations';


// ============================================================================
// Client State Enum
// ============================================================================

export enum ClientState {
  Synchronized = 'synchronized',
  AwaitingConfirm = 'awaiting_confirm',
  AwaitingWithBuffer = 'awaiting_with_buffer'
}

// ============================================================================
// OT Client Class
// ============================================================================

export class OTClient {
  private state: ClientState = ClientState.Synchronized;
  private revision: number = 0;
  private outstanding: TextOperation | null = null;
  private buffer: TextOperation | null = null;

  private sendOperation: (operation: TextOperation) => void;
  private applyOperation: (operation: TextOperation) => void;

  /**
   * @param revision Initial revision number from server
   * @param sendOperation Callback to send operation to server
   * @param applyOperation Callback to apply operation to editor
   */
  constructor(
    revision: number,
    sendOperation: (operation: TextOperation) => void,
    applyOperation: (operation: TextOperation) => void
  ) {
    this.revision = revision;
    this.sendOperation = sendOperation;
    this.applyOperation = applyOperation;
  }

  /**
   * Apply a local operation (from user editing)
   */
  applyClient(operation: TextOperation): void {
    if (operation.isNoop()) {
      return;
    }

    switch (this.state) {
      case ClientState.Synchronized:
        // Send immediately
        this.sendOperation(operation);
        this.setState(ClientState.AwaitingConfirm);
        this.outstanding = operation;
        break;

      case ClientState.AwaitingConfirm:
        // Buffer the operation
        this.buffer = operation;
        this.setState(ClientState.AwaitingWithBuffer);
        break;

      case ClientState.AwaitingWithBuffer:
        // Compose with existing buffer
        if (this.buffer) {
          this.buffer = this.buffer.compose(operation);
        } else {
          this.buffer = operation;
        }
        break;
    }
  }

  /**
   * Apply a remote operation (from server)
   */
  applyServer(operation: TextOperation): void {
    this.revision++;

    switch (this.state) {
      case ClientState.Synchronized:
        // Simply apply the operation
        this.applyOperation(operation);
        break;

      case ClientState.AwaitingConfirm:
        // Transform outstanding operation against server operation
        if (this.outstanding) {
          const [outstanding1, operation1] = transform(this.outstanding, operation, 'left');
          this.outstanding = outstanding1;
          this.applyOperation(operation1);
        }
        break;

      case ClientState.AwaitingWithBuffer:
        // Transform both outstanding and buffer against server operation
        if (this.outstanding && this.buffer) {
          const [outstanding1, operation1] = transform(this.outstanding, operation, 'left');
          const [buffer1, operation2] = transform(this.buffer, operation1, 'left');
          this.outstanding = outstanding1;
          this.buffer = buffer1;
          this.applyOperation(operation2);
        } else if (this.outstanding) {
          const [outstanding1, operation1] = transform(this.outstanding, operation, 'left');
          this.outstanding = outstanding1;
          this.applyOperation(operation1);
        }
        break;
    }
  }

  /**
   * Handle acknowledgment from server (our operation was applied)
   */
  serverAck(): void {
    this.revision++;

    switch (this.state) {
      case ClientState.AwaitingConfirm:
        // Acknowledged! Back to synchronized
        this.setState(ClientState.Synchronized);
        this.outstanding = null;
        break;

      case ClientState.AwaitingWithBuffer:
        // Send buffered operation
        if (this.buffer) {
          this.sendOperation(this.buffer);
          this.outstanding = this.buffer;
          this.buffer = null;
          this.setState(ClientState.AwaitingConfirm);
        }
        break;

      case ClientState.Synchronized:
        console.warn('[OTClient] Received ACK in synchronized state');
        break;
    }
  }

  /**
   * Handle operation rejection from server
   */
  serverReject(): void {
    console.error('[OTClient] Server rejected operation');

    // Reset to synchronized state
    this.setState(ClientState.Synchronized);
    this.outstanding = null;
    this.buffer = null;

    // Could emit event for UI notification
  }

  /**
   * Get current state
   */
  getState(): ClientState {
    return this.state;
  }

  /**
   * Get current revision
   */
  getRevision(): number {
    return this.revision;
  }

  /**
   * Check if client is synchronized
   */
  isSynchronized(): boolean {
    return this.state === ClientState.Synchronized;
  }

  /**
   * Check if there are pending operations
   */
  hasPendingOperations(): boolean {
    return this.outstanding !== null || this.buffer !== null;
  }

  /**
   * Get debug info
   */
  getDebugInfo(): any {
    return {
      state: this.state,
      revision: this.revision,
      outstanding: this.outstanding ? this.outstanding.toString() : null,
      buffer: this.buffer ? this.buffer.toString() : null
    };
  }

  /**
   * Set state and log transition
   */
  private setState(newState: ClientState): void {
    const oldState = this.state;
    this.state = newState;
    console.log(`[OTClient] State transition: ${oldState} → ${newState}`);
  }
}
