/**
 * Server Status - Main Entry Point
 *
 * Pre-rendered charts are served from backend (generated every 1 min by Celery).
 * This module handles:
 * - Time span selection (1h, 6h, 24h)
 * - Theme-aware chart loading
 * - Real-time metric value updates
 * - Visitor countdown timers
 * - Session expiration detection (stops polling to prevent server overload)
 */

import { updateMetrics } from './_server-status/metrics-updater';
import { updateVisitorCountdowns } from './_server-status/visitor-countdown';


// State
let currentTimeSpanMinutes = 60;

// Track intervals for cleanup on session expiration
let chartIntervalId: number | null = null;
let metricsIntervalId: number | null = null;
let countdownIntervalId: number | null = null;
let consecutiveErrors = 0;
const MAX_CONSECUTIVE_ERRORS = 5;

/**
 * Stop all polling intervals (called when session expires or too many errors)
 */
function stopAllPolling(reason: string): void {
  console.log(`[server-status] Stopping all polling: ${reason}`);

  if (chartIntervalId) {
    clearInterval(chartIntervalId);
    chartIntervalId = null;
  }
  if (metricsIntervalId) {
    clearInterval(metricsIntervalId);
    metricsIntervalId = null;
  }
  if (countdownIntervalId) {
    clearInterval(countdownIntervalId);
    countdownIntervalId = null;
  }
}

// Expose stop function globally for other modules
(window as unknown as Record<string, unknown>).stopServerStatusPolling = stopAllPolling;

/**
 * Get current theme from document
 */
function getCurrentTheme(): string {
  return document.documentElement.getAttribute('data-theme') || 'dark';
}

/**
 * Update all chart images with current time span and theme
 */
function updateChartImages(): void {
  const imgs = document.querySelectorAll('.matplotlib-chart') as NodeListOf<HTMLImageElement>;
  const timestamp = Date.now(); // Cache buster
  const theme = getCurrentTheme();

  imgs.forEach(img => {
    const metric = img.dataset.metric;
    if (metric) {
      img.src = `/api/server-metrics/chart/${metric}/?minutes=${currentTimeSpanMinutes}&theme=${theme}&t=${timestamp}`;
    }
  });
}

/**
 * Setup time span selector buttons
 */
function setupTimeSpanSelector(): void {
  const selector = document.getElementById('timeSpanSelector');
  if (!selector) return;

  selector.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;
    if (!target.classList.contains('time-span-btn')) return;

    const minutes = parseInt(target.dataset.minutes || '60', 10);
    if (minutes === currentTimeSpanMinutes) return;

    // Update button states
    selector.querySelectorAll('.time-span-btn').forEach(btn => {
      btn.classList.remove('active');
    });
    target.classList.add('active');

    // Update time span and refresh charts
    currentTimeSpanMinutes = minutes;
    updateChartImages();
  });
}

/**
 * Setup theme change listener
 */
function setupThemeListener(): void {
  // Listen for theme changes
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.attributeName === 'data-theme') {
        console.log('[server-status] Theme changed, updating charts...');
        updateChartImages();
        break;
      }
    }
  });

  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme']
  });
}

/**
 * Wrapper for updateMetrics that tracks errors and stops polling if too many failures
 */
async function safeUpdateMetrics(): Promise<void> {
  try {
    const result = await updateMetrics();
    // Check if session expired (returned from metrics-updater)
    if (result && result.sessionExpired) {
      stopAllPolling('Session expired');
      window.location.replace('/visitor-expired/');
      return;
    }
    consecutiveErrors = 0; // Reset on success
  } catch {
    consecutiveErrors++;
    console.warn(`[server-status] Metrics error (${consecutiveErrors}/${MAX_CONSECUTIVE_ERRORS})`);
    if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
      stopAllPolling('Too many consecutive errors');
    }
  }
}

/**
 * Initialize server status page
 */
function initializeServerStatus(): void {
  // Setup UI handlers
  setupTimeSpanSelector();
  setupThemeListener();

  // Load charts immediately
  updateChartImages();

  // Refresh charts every 60 seconds (matches Celery generation interval)
  chartIntervalId = window.setInterval(updateChartImages, 60000);

  // Update metric values every 2 seconds
  safeUpdateMetrics();
  metricsIntervalId = window.setInterval(safeUpdateMetrics, 2000);

  console.log('[server-status] Initialized - charts refresh every 60s, metrics every 2s');
}

// Initialize on page load
window.addEventListener('load', function() {
  initializeServerStatus();

  // Update visitor pool countdowns every second
  updateVisitorCountdowns();
  countdownIntervalId = window.setInterval(updateVisitorCountdowns, 1000);
});
