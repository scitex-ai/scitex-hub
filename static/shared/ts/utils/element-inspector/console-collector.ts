/**
 * Console Collector for Element Inspector
 * Captures console logs and provides debug snapshot functionality
 */

import { NotificationManager } from "./notification-manager.js";

interface ConsoleEntry {
  type: "log" | "warn" | "error" | "info" | "debug";
  timestamp: string;
  args: string[];
  source: string;
}

export class ConsoleCollector {
  private notificationManager: NotificationManager;
  private consoleLogs: ConsoleEntry[] = [];
  private networkErrors: string[] = [];
  private maxLogs: number = 1000;
  private isCapturing: boolean = false;

  // Store original console methods
  private originalConsole: {
    log: typeof console.log;
    warn: typeof console.warn;
    error: typeof console.error;
    info: typeof console.info;
    debug: typeof console.debug;
  };

  constructor(notificationManager: NotificationManager) {
    this.notificationManager = notificationManager;
    this.originalConsole = {
      log: console.log.bind(console),
      warn: console.warn.bind(console),
      error: console.error.bind(console),
      info: console.info.bind(console),
      debug: console.debug.bind(console),
    };

    // Start capturing immediately
    this.startCapturing();
    // Also capture network errors
    this.captureNetworkErrors();
  }

  /**
   * Capture network errors (404s, etc.) using Performance API
   */
  private captureNetworkErrors(): void {
    // Listen for future resource errors
    window.addEventListener("error", (e) => {
      if (e.target && (e.target as HTMLElement).tagName) {
        const target = e.target as HTMLElement;
        const src = (target as any).src || (target as any).href || "";
        if (src) {
          this.networkErrors.push(`Failed to load resource: ${src}`);
        }
      }
    }, true);
  }

  private startCapturing(): void {
    if (this.isCapturing) return;
    this.isCapturing = true;

    const self = this;

    // Override console methods to capture logs
    console.log = function (...args: any[]) {
      self.captureLog("log", args);
      self.originalConsole.log.apply(console, args);
    };

    console.warn = function (...args: any[]) {
      self.captureLog("warn", args);
      self.originalConsole.warn.apply(console, args);
    };

    console.error = function (...args: any[]) {
      self.captureLog("error", args);
      self.originalConsole.error.apply(console, args);
    };

    console.info = function (...args: any[]) {
      self.captureLog("info", args);
      self.originalConsole.info.apply(console, args);
    };

    console.debug = function (...args: any[]) {
      self.captureLog("debug", args);
      self.originalConsole.debug.apply(console, args);
    };
  }

  private captureLog(
    type: "log" | "warn" | "error" | "info" | "debug",
    args: any[],
  ): void {
    const entry: ConsoleEntry = {
      type,
      timestamp: new Date().toISOString(),
      args: args.map((arg) => this.stringify(arg)),
      source: this.getCallSource(),
    };

    this.consoleLogs.push(entry);

    // Keep only the last maxLogs entries
    if (this.consoleLogs.length > this.maxLogs) {
      this.consoleLogs.shift();
    }
  }

  /**
   * Get the source file and line number of the console call
   */
  private getCallSource(): string {
    try {
      const stack = new Error().stack;
      if (!stack) return "";

      const lines = stack.split("\n");
      // Skip: Error, getCallSource, captureLog, console.xxx override, actual caller
      for (let i = 4; i < lines.length; i++) {
        const line = lines[i];
        // Match file:line:col pattern
        const match = line.match(/(?:at\s+)?(?:.*?\s+\()?([^\s()]+):(\d+):(\d+)\)?$/);
        if (match) {
          const [, file, lineNum] = match;
          // Clean up file path - get just filename
          const fileName = file.split("/").pop() || file;
          // Skip internal files
          if (fileName.includes("console-collector")) continue;
          return `${fileName}:${lineNum}`;
        }
      }
    } catch (e) {
      // Ignore errors
    }
    return "";
  }

  private stringify(obj: any): string {
    if (obj === null) return "null";
    if (obj === undefined) return "undefined";
    if (typeof obj === "string") return obj;
    if (typeof obj === "number" || typeof obj === "boolean") return String(obj);
    if (obj instanceof Error) {
      return `${obj.name}: ${obj.message}\n${obj.stack || ""}`;
    }
    try {
      return JSON.stringify(obj, null, 2);
    } catch (e) {
      return String(obj);
    }
  }

  public getConsoleLogs(): string {
    // Try to get logs from the global console interceptor first (captures everything since page load)
    const globalInterceptor = (window as any).__consoleInterceptor;
    if (globalInterceptor && typeof globalInterceptor.getDevToolsFormat === "function") {
      const logs = globalInterceptor.getDevToolsFormat();
      if (logs && logs !== "No console logs captured.") {
        return logs;
      }
    }

    // Fallback to our own captured logs
    const failedResources = this.getFailedResources();
    const totalEntries = this.consoleLogs.length + failedResources.length + this.networkErrors.length;

    if (totalEntries === 0) {
      return "No console logs captured.";
    }

    let output = "";

    // Add failed resources first (these are typically 404 errors)
    if (failedResources.length > 0) {
      failedResources.forEach((resource) => {
        output += `❌ Failed to load resource: the server responded with a status of 404 (Not Found)\n`;
        output += `   ${resource}\n`;
      });
    }

    // Add captured network errors
    if (this.networkErrors.length > 0) {
      this.networkErrors.forEach((error) => {
        output += `❌ ${error}\n`;
      });
    }

    // Add console logs with source info like browser DevTools
    this.consoleLogs.forEach((entry) => {
      const source = entry.source ? `${entry.source} ` : "";
      output += `${source}${entry.args.join(" ")}\n`;
    });

    return output;
  }

  /**
   * Get failed resources from Performance API
   */
  private getFailedResources(): string[] {
    const failed: string[] = [];

    if (window.performance && window.performance.getEntriesByType) {
      const resources = window.performance.getEntriesByType("resource") as PerformanceResourceTiming[];

      // Check for resources with transferSize = 0 and no cache (likely 404)
      // Also check responseStatus if available (newer browsers)
      resources.forEach((r) => {
        // If responseStatus is available and not 2xx/3xx, it's an error
        if ((r as any).responseStatus && (r as any).responseStatus >= 400) {
          failed.push(r.name);
        }
      });
    }

    return failed;
  }

  private getTypeIcon(type: string): string {
    switch (type) {
      case "error":
        return "❌";
      case "warn":
        return "⚠️";
      case "info":
        return "ℹ️";
      case "debug":
        return "🔍";
      default:
        return "📝";
    }
  }

  public async captureDebugSnapshot(): Promise<void> {
    // Show flash
    this.notificationManager.showCameraFlash();

    // Run screenshot and console log capture in parallel
    const [screenshotResult, logsResult] = await Promise.all([
      this.captureScreenshot(),
      this.captureConsoleLogs(),
    ]);

    // Report results
    const results: string[] = [];
    if (screenshotResult) results.push("screenshot");
    if (logsResult) results.push("logs");

    if (results.length === 2) {
      this.notificationManager.showNotification("✓ Screenshot + logs copied", "success");
    } else if (results.length === 1) {
      this.notificationManager.showNotification(`✓ ${results[0]} copied`, "success");
    } else {
      this.notificationManager.showNotification("✗ Capture failed", "error");
    }

    this.notificationManager.triggerCopyCallback();
  }

  /**
   * Capture screenshot using getDisplayMedia (OS-level capture)
   * Returns true if successful
   */
  private async captureScreenshot(): Promise<boolean> {
    try {
      // Use getDisplayMedia with preferCurrentTab for auto-selection
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          displaySurface: "browser",
        } as MediaTrackConstraints,
        preferCurrentTab: true,
        selfBrowserSurface: "include",
        systemAudio: "exclude",
      } as DisplayMediaStreamOptions);

      const video = document.createElement("video");
      video.srcObject = stream;
      video.muted = true;

      await new Promise<void>((resolve, reject) => {
        video.onloadedmetadata = () => {
          video.play().then(() => resolve()).catch(reject);
        };
        video.onerror = reject;
        setTimeout(() => reject(new Error("Video load timeout")), 3000);
      });

      // Small delay to ensure frame is rendered
      await new Promise((r) => setTimeout(r, 100));

      // Capture frame to canvas
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        stream.getTracks().forEach((t) => t.stop());
        return false;
      }

      ctx.drawImage(video, 0, 0);
      stream.getTracks().forEach((t) => t.stop());

      // Convert to blob and copy to clipboard
      const blob = await new Promise<Blob | null>((resolve) => {
        canvas.toBlob((b) => resolve(b), "image/png");
      });

      if (!blob) return false;

      await navigator.clipboard.write([
        new ClipboardItem({ "image/png": blob }),
      ]);

      return true;
    } catch (err) {
      // User cancelled or permission denied
      if ((err as Error).name !== "NotAllowedError") {
        this.originalConsole.error("[ConsoleCollector] Screenshot failed:", err);
      }
      return false;
    }
  }

  /**
   * Capture console logs and copy to clipboard
   * Returns true if successful
   */
  private async captureConsoleLogs(): Promise<boolean> {
    try {
      const textSnapshot = this.getConsoleLogs();
      await navigator.clipboard.writeText(textSnapshot);
      return true;
    } catch (e) {
      this.originalConsole.error("[ConsoleCollector] Failed to copy logs:", e);
      return false;
    }
  }

  public clearLogs(): void {
    this.consoleLogs = [];
    this.originalConsole.log("[ConsoleCollector] Logs cleared");
  }
}
