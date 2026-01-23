/**
 * Server Status - Main Entry Point
 *
 * Pre-rendered charts are served from backend (generated every 1 min by Celery).
 * This module handles:
 * - Time span selection (1h, 6h, 24h)
 * - Theme-aware chart loading
 * - Real-time metric value updates
 * - Visitor countdown timers
 */

import { updateMetrics } from './server-status/metrics-updater.ts';
import { updateVisitorCountdowns } from './server-status/visitor-countdown.ts';

console.log('[DEBUG] server-status.ts loaded');

// State
let currentTimeSpanMinutes = 60;

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
 * Initialize server status page
 */
function initializeServerStatus(): void {
  // Setup UI handlers
  setupTimeSpanSelector();
  setupThemeListener();

  // Load charts immediately
  updateChartImages();

  // Refresh charts every 60 seconds (matches Celery generation interval)
  setInterval(updateChartImages, 60000);

  // Update metric values every 2 seconds
  updateMetrics();
  setInterval(updateMetrics, 2000);

  console.log('[server-status] Initialized - charts refresh every 60s, metrics every 2s');
}

// Initialize on page load
window.addEventListener('load', function() {
  initializeServerStatus();

  // Update visitor pool countdowns every second
  setInterval(updateVisitorCountdowns, 1000);
  updateVisitorCountdowns();
});
