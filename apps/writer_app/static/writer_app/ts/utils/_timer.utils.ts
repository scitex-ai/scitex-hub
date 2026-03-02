/**
 * Timer and debounce/throttle utilities
 */

/**
 * Debounce function to delay execution
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/utils/timer.utils.ts loaded",
);
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  immediate: boolean = false,
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      if (!immediate) func(...args);
    };

    const callNow = immediate && !timeout;
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(later, wait);

    if (callNow) func(...args);
  };
}

/**
 * Throttle function to limit execution frequency
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number,
): (...args: Parameters<T>) => void {
  let inThrottle: boolean = false;

  return function executedFunction(...args: Parameters<T>) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

/**
 * Format elapsed time for display
 */
export function formatElapsedTime(milliseconds: number): string {
  const totalSeconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

/**
 * Create a simple timer
 */
export class SimpleTimer {
  private startTime: number = 0;
  private isRunning: boolean = false;
  private interval?: NodeJS.Timeout;

  start(onTick?: (elapsed: number) => void): void {
    this.startTime = Date.now();
    this.isRunning = true;

    if (onTick) {
      this.interval = setInterval(() => {
        if (this.isRunning) {
          const elapsed = Date.now() - this.startTime;
          onTick(elapsed);
        }
      }, 100);
    }
  }

  stop(): number {
    this.isRunning = false;
    if (this.interval) {
      clearInterval(this.interval);
    }
    return Date.now() - this.startTime;
  }

  getElapsed(): number {
    if (!this.isRunning) return 0;
    return Date.now() - this.startTime;
  }

  reset(): void {
    this.stop();
    this.startTime = 0;
  }

  isActive(): boolean {
    return this.isRunning;
  }
}

/**
 * Wait for specified time
 */
export function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Create a cancellable timeout
 */
export function createTimeout(
  callback: () => void,
  ms: number,
): { cancel: () => void } {
  const timeout = setTimeout(callback, ms);
  return {
    cancel: () => clearTimeout(timeout),
  };
}
