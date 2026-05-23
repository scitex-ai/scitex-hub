/**
 * Tests for static/shared/ts/utils/console-interceptor.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '@/static/shared/ts/utils/console-interceptor';

describe('console-interceptor', () => {
    beforeEach(() => {
        // Setup before each test
    });

    afterEach(() => {
        // Cleanup after each test
    });

    it.todo('should be implemented');
});

// =============================================================================
// Source Code Reference (auto-generated, do not edit below this line)
// =============================================================================
// Source: static/shared/ts/utils/console-interceptor.ts
// =============================================================================

// /**
//  * Console Interceptor - Tee-like functionality for console logs
//  *
//  * Captures console.log, console.info, console.warn, console.error
//  * and sends them to server to be written to ./logs/console.log
//  *
//  * Works like `tee`:
//  * - Shows in browser DevTools (stdout)
//  * - Writes to file on server (file)
//  */
//
// console.log(
//   "[DEBUG] /home/ywatanabe/proj/scitex-hub/static/ts/utils/console-interceptor.ts loaded",
// );
// interface ConsoleLogEntry {
//   level: string;
//   message: string;
//   source: string;
//   timestamp: number;
//   url: string;
// }
//
// class ConsoleInterceptor {
//   private buffer: ConsoleLogEntry[] = [];
//   private history: ConsoleLogEntry[] = []; // Full history for debug snapshots
//   private maxHistory: number = 2000;
//   private batchInterval: number = 1000; // 1 second
//   private maxBatchSize: number = 50;
//   private apiEndpoint: string = "/dev/api/console/";
//   private enabled: boolean = false;
//
//   // Store original console methods
//   private originalConsole = {
//     log: console.log,
//     info: console.info,
//     warn: console.warn,
//     error: console.error,
//     debug: console.debug,
//   };
//
//   constructor() {
//     // Only enable in development
//     this.enabled =
//       document.documentElement.hasAttribute("data-debug") ||
//       window.location.hostname === "localhost" ||
//       window.location.hostname === "127.0.0.1";
//
//     if (this.enabled) {
//       this.init();
//     }
//   }
//
//   private init(): void {
//     this.interceptConsoleMethods();
//     this.interceptErrors();
//     this.startBatchSender();
//     console.info(
//       "[Console Interceptor] Active - logs will be saved to ./logs/console.log",
//     );
//   }
//
//   /**
//    * Capture unhandled errors and failed resource loads
//    */
//   private interceptErrors(): void {
//     // Capture unhandled JavaScript errors
//     window.addEventListener("error", (event) => {
//       if (event.target && (event.target as any).tagName) {
//         // This is a resource loading error (img, script, link, etc.)
//         const target = event.target as HTMLElement;
//         const src = (target as any).src || (target as any).href || "";
//         if (src) {
//           const entry: ConsoleLogEntry = {
//             level: "error",
//             message: `Failed to load resource: the server responded with a status of 404 (Not Found)\n${src}`,
//             source: src.split("/").pop() || "",
//             timestamp: Date.now(),
//             url: window.location.href,
//           };
//           this.history.push(entry);
//           this.buffer.push(entry);
//         }
//       } else {
//         // This is a JavaScript error
//         const entry: ConsoleLogEntry = {
//           level: "error",
//           message: `${event.message}`,
//           source: `${event.filename}:${event.lineno}:${event.colno}`,
//           timestamp: Date.now(),
//           url: window.location.href,
//         };
//         this.history.push(entry);
//         this.buffer.push(entry);
//       }
//     }, true);
//
//     // Capture unhandled promise rejections
//     window.addEventListener("unhandledrejection", (event) => {
//       const entry: ConsoleLogEntry = {
//         level: "error",
//         message: `Uncaught (in promise): ${event.reason}`,
//         source: "",
//         timestamp: Date.now(),
//         url: window.location.href,
//       };
//       this.history.push(entry);
//       this.buffer.push(entry);
//     });
//   }
//
//   private interceptConsoleMethods(): void {
//     const self = this;
//
//     // Intercept console.log
//     console.log = function (...args: any[]) {
//       self.originalConsole.log.apply(console, args);
//       self.capture("log", args);
//     };
//
//     // Intercept console.info
//     console.info = function (...args: any[]) {
//       self.originalConsole.info.apply(console, args);
//       self.capture("info", args);
//     };
//
//     // Intercept console.warn
//     console.warn = function (...args: any[]) {
//       self.originalConsole.warn.apply(console, args);
//       self.capture("warn", args);
//     };
//
//     // Intercept console.error
//     console.error = function (...args: any[]) {
//       self.originalConsole.error.apply(console, args);
//       self.capture("error", args);
//     };
//
//     // Intercept console.debug
//     console.debug = function (...args: any[]) {
//       self.originalConsole.debug.apply(console, args);
//       self.capture("debug", args);
//     };
//   }
//
//   private capture(level: string, args: any[]): void {
//     const message = this.formatMessage(args);
//     const source = this.getSource();
//
//     const entry: ConsoleLogEntry = {
//       level,
//       message,
//       source,
//       timestamp: Date.now(),
//       url: window.location.href,
//     };
//
//     this.buffer.push(entry);
//
//     // Also keep in history for debug snapshots
//     this.history.push(entry);
//     if (this.history.length > this.maxHistory) {
//       this.history.shift();
//     }
//
//     // Send immediately if buffer is full
//     if (this.buffer.length >= this.maxBatchSize) {
//       this.sendBatch();
//     }
//   }
//
//   /**
//    * Get all captured console logs as formatted text (like browser DevTools)
//    */
//   public getFormattedLogs(): string {
//     if (this.history.length === 0) {
//       return "No console logs captured.";
//     }
//
//     let output = "";
//     this.history.forEach((entry) => {
//       const levelIcon = this.getLevelIcon(entry.level);
//       const source = entry.source ? ` ${entry.source}` : "";
//       output += `${entry.source}${source ? "" : ""} ${entry.message}\n`;
//     });
//
//     return output;
//   }
//
//   /**
//    * Get logs in DevTools-like format
//    */
//   public getDevToolsFormat(): string {
//     if (this.history.length === 0) {
//       return "No console logs captured.";
//     }
//
//     let output = "";
//     this.history.forEach((entry) => {
//       // Format: source:line message
//       // e.g., console-interceptor.ts:64 [ElementInspector] Initialized
//       const source = entry.source || "unknown";
//       output += `${source} ${entry.message}\n`;
//     });
//
//     return output;
//   }
//
//   private getLevelIcon(level: string): string {
//     switch (level) {
//       case "error": return "❌";
//       case "warn": return "⚠️";
//       case "info": return "ℹ️";
//       case "debug": return "🔍";
//       default: return "📝";
//     }
//   }
//
//   /**
//    * Get the history array directly
//    */
//   public getHistory(): ConsoleLogEntry[] {
//     return [...this.history];
//   }
//
//   private formatMessage(args: any[]): string {
//     return args
//       .map((arg) => {
//         if (typeof arg === "object") {
//           try {
//             return JSON.stringify(arg, null, 2);
//           } catch (e) {
//             return String(arg);
//           }
//         }
//         return String(arg);
//       })
//       .join(" ");
//   }
//
//   private getSource(): string {
//     try {
//       const stack = new Error().stack;
//       if (!stack) return "";
//
//       // Parse stack trace to get calling file and line
//       const lines = stack.split("\n");
//       // Skip first 3 lines (Error, getSource, capture)
//       for (let i = 3; i < lines.length; i++) {
//         const line = lines[i];
//         // Match file:line:col pattern
//         const match = line.match(/(?:https?:\/\/[^\/]+)?([^\s]+):(\d+):(\d+)/);
//         if (match) {
//           const [, file, lineNum, col] = match;
//           // Clean up file path
//           const cleanFile = file.split("/").slice(-2).join("/");
//           return `${cleanFile}:${lineNum}:${col}`;
//         }
//       }
//     } catch (e) {
//       // Ignore errors
//     }
//     return "";
//   }
//
//   private startBatchSender(): void {
//     setInterval(() => {
//       if (this.buffer.length > 0) {
//         this.sendBatch();
//       }
//     }, this.batchInterval);
//   }
//
//   private async sendBatch(): Promise<void> {
//     if (this.buffer.length === 0) return;
//
//     const logs = this.buffer.splice(0, this.maxBatchSize);
//
//     try {
//       const response = await fetch(this.apiEndpoint, {
//         method: "POST",
//         headers: {
//           "Content-Type": "application/json",
//         },
//         body: JSON.stringify({ logs }),
//       });
//
//       if (!response.ok) {
//         // Use original console to avoid recursion
//         this.originalConsole.warn(
//           `[Console Interceptor] Failed to send logs: ${response.status}`,
//         );
//       }
//     } catch (error) {
//       // Use original console to avoid recursion
//       this.originalConsole.warn("[Console Interceptor] Network error:", error);
//     }
//   }
// }
//
// // Auto-initialize when script loads and expose globally
// if (typeof window !== "undefined") {
//   const interceptor = new ConsoleInterceptor();
//   // Expose globally for Element Inspector to access
//   (window as any).__consoleInterceptor = interceptor;
// }

// =============================================================================
// End of Source Code
// =============================================================================
