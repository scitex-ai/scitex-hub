/**
 * API Documentation page functionality
 * Handles tabs, copy-to-clipboard, smooth scrolling, and sidebar navigation
 */

// Dynamic base URL for self-hosted instances
const SITE_BASE_URL = window.location.origin;

/**
 * Initialize the API docs page
 */
function initApiDocs(): void {
  // Set base URL display
  const baseUrlEl = document.getElementById('site-base-url');
  if (baseUrlEl) {
    baseUrlEl.textContent = SITE_BASE_URL;
  }

  // Replace all hardcoded URLs in code examples
  replaceHardcodedUrls();

  // Setup tab switching
  setupTabs();

  // Setup copy to clipboard
  setupCopyButtons();

  // Setup smooth scroll for sidebar links
  setupSmoothScroll();

  // Setup active section highlighting
  setupSectionObserver();
}

/**
 * Replace hardcoded scitex.ai URLs with current site URL
 */
function replaceHardcodedUrls(): void {
  document.querySelectorAll('pre code').forEach(block => {
    if (block.textContent) {
      block.textContent = block.textContent.replace(/https:\/\/scitex\.ai/g, SITE_BASE_URL);
    }
  });
}

/**
 * Setup tab switching functionality
 */
function setupTabs(): void {
  document.querySelectorAll('.api-tab').forEach(tab => {
    tab.addEventListener('click', function(this: HTMLElement) {
      const tabId = this.dataset.tab;
      if (!tabId) return;

      const parent = this.closest('.api-section');
      if (!parent) return;

      // Update active tab
      parent.querySelectorAll('.api-tab').forEach(t => t.classList.remove('active'));
      this.classList.add('active');

      // Update active content
      parent.querySelectorAll('.api-tab-content').forEach(c => c.classList.remove('active'));
      const targetContent = document.getElementById(tabId);
      if (targetContent) {
        targetContent.classList.add('active');
      }
    });
  });
}

/**
 * Setup copy to clipboard buttons
 */
function setupCopyButtons(): void {
  document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', function(this: HTMLElement) {
      const targetId = this.dataset.copy;
      if (!targetId) return;

      const target = document.getElementById(targetId);
      if (target && target.textContent) {
        navigator.clipboard.writeText(target.textContent).then(() => {
          const icon = this.querySelector('i');
          if (icon) {
            icon.className = 'fas fa-check';
            setTimeout(() => {
              icon.className = 'fas fa-copy';
            }, 2000);
          }
        });
      }
    });
  });
}

/**
 * Setup smooth scroll for sidebar links
 */
function setupSmoothScroll(): void {
  document.querySelectorAll('.api-nav a').forEach(link => {
    link.addEventListener('click', function(this: HTMLAnchorElement, e: Event) {
      e.preventDefault();
      const href = this.getAttribute('href');
      if (!href) return;

      const target = document.querySelector(href);
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        // Update URL without scrolling
        history.pushState(null, '', href);
      }
    });
  });
}

/**
 * Setup intersection observer to highlight active section in sidebar
 */
function setupSectionObserver(): void {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        document.querySelectorAll('.api-nav a').forEach(link => {
          const href = link.getAttribute('href');
          link.classList.toggle('active', href === '#' + id);
        });
      }
    });
  }, { threshold: 0.2, rootMargin: '-100px 0px -60% 0px' });

  document.querySelectorAll('.api-section[id]').forEach(section => {
    observer.observe(section);
  });
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initApiDocs);
