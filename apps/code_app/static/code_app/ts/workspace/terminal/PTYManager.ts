/**
 * PTY Terminal Manager
 * Handles PTY terminal initialization and management with tab support
 */

import { PTYTerminal } from "../../pty-terminal.js";
import { TerminalTabManager } from "./TerminalTabManager.js";
import type { EditorConfig } from "../core/types.js";

export class PTYManager {
  private terminalTabManager: TerminalTabManager;
  private config: EditorConfig;

  constructor(config: EditorConfig) {
    this.config = config;
    this.terminalTabManager = new TerminalTabManager(config);
  }

  async initialize(): Promise<void> {
    await this.terminalTabManager.initialize();
    console.log("[PTYManager] Terminal tab manager initialized");
  }

  /**
   * Get active terminal
   */
  getTerminal(): PTYTerminal | null {
    return this.terminalTabManager.getActiveTerminal();
  }

  /**
   * Get terminal tab manager for advanced operations
   */
  getTabManager(): TerminalTabManager {
    return this.terminalTabManager;
  }

  /**
   * Create a new terminal tab
   */
  async createNewTerminal(name?: string): Promise<void> {
    await this.terminalTabManager.createTerminal(name);
  }

  /**
   * Switch to next terminal tab
   */
  switchToNextTab(): void {
    this.terminalTabManager.switchToNextTab();
  }

  /**
   * Switch to previous terminal tab
   */
  switchToPrevTab(): void {
    this.terminalTabManager.switchToPrevTab();
  }

  sendCommand(command: string): void {
    const terminal = this.getTerminal();
    if (!terminal) {
      console.error("[PTYManager] Terminal not initialized");
      return;
    }

    // PTYTerminal handles command execution via write method
    console.log("[PTYManager] Sending command:", command);
  }

  /**
   * Update terminal theme when global theme changes
   */
  updateTheme(): void {
    this.terminalTabManager.updateTheme();
  }

  /**
   * Get total number of terminals
   */
  getTerminalCount(): number {
    return this.terminalTabManager.getTerminalCount();
  }
}
