/**
 * API Documentation page functionality
 * Handles tabs, copy-to-clipboard, smooth scrolling, sidebar navigation,
 * and per-example environment/auth switchers
 */

interface ApiSettings {
  localUrl: string;
  cloudUrl: string;
  campaignToken: string;
  userApiKey: string;
  isAuthenticated: boolean;
  username: string;
  testPassword: string;
}

let apiSettings: ApiSettings | null = null;

/**
 * Load API settings from embedded JSON
 */
function loadApiSettings(): ApiSettings {
  if (apiSettings) return apiSettings;

  const dataEl = document.getElementById("api-settings-data");
  if (dataEl) {
    try {
      apiSettings = JSON.parse(dataEl.textContent || "{}");
    } catch {
      apiSettings = {
        localUrl: window.location.origin,
        cloudUrl: "https://scitex.ai",
        campaignToken: "",
        userApiKey: "",
        isAuthenticated: false,
        username: "",
        testPassword: "",
      };
    }
  }
  return apiSettings!;
}

/**
 * Initialize the API docs page
 */
function initApiDocs(): void {
  loadApiSettings();

  // Inject switchers into all code examples
  injectCodeExampleSwitchers();

  // Setup tab switching
  setupTabs();

  // Setup example-specific tabs (Generic vs Campaign)
  setupExampleTabs();

  // Setup copy to clipboard
  setupCopyButtons();

  // Setup smooth scroll for sidebar links
  setupSmoothScroll();

  // Setup active section highlighting
  setupSectionObserver();

  // Setup download dropdown
  setupDownloadDropdown();

  // Setup internal API group toggle
  setupInternalToggle();

  // Setup info card switchers
  setupCardSwitchers();
}

/**
 * Mask sensitive token for display (show first 8 and last 5 chars)
 */
function maskToken(token: string): string {
  if (token.length <= 16) return "***masked***";
  return token.slice(0, 8) + "***" + token.slice(-5);
}

/**
 * Inject General/Private switcher into every code example
 * - General: Shows generic placeholders (YOUR_TOKEN, your_username, your_password)
 * - Private: Shows actual username and token (masked with eye toggle), password as <YOUR_PASSWORD>
 */
function injectCodeExampleSwitchers(): void {
  const settings = loadApiSettings();

  // Determine the actual values to use
  const actualToken =
    settings.userApiKey || settings.campaignToken || "YOUR_TOKEN";
  const maskedToken = maskToken(actualToken);
  // Username is not sensitive - show it directly
  const actualUsername = settings.username || "your_username";
  // Password: always use placeholder (user passwords cannot be retrieved from Django)
  const passwordPlaceholder = "<YOUR_PASSWORD>";

  document.querySelectorAll(".api-example").forEach((example) => {
    const header = example.querySelector(".api-example-header");
    const codeBlock = example.querySelector("pre code");

    if (!codeBlock) return;

    // Store original content (with generic placeholders)
    const originalContent = codeBlock.textContent || "";

    // Skip if no token placeholders in this example
    const hasTokenPlaceholder =
      /YOUR_TOKEN|your_username|your_password|your-api-key/i.test(
        originalContent,
      );
    if (!hasTokenPlaceholder) return;

    // Create switcher HTML with eye toggle (always visible, disabled when General)
    const switcherHtml = document.createElement("div");
    switcherHtml.className = "code-env-switcher";
    switcherHtml.innerHTML = `
      <button class="env-btn active" data-mode="general" title="Generic example">
        <i class="fas fa-code"></i> General
      </button>
      <button class="env-btn" data-mode="private" title="Ready to run with your credentials">
        <i class="fas fa-key"></i> Private
      </button>
      <button class="env-btn eye-toggle disabled" data-visible="false" title="Toggle token visibility (enable Private mode first)">
        <i class="fas fa-eye-slash"></i>
      </button>
    `;

    // Insert switcher
    if (header) {
      header.appendChild(switcherHtml);
    } else {
      const newHeader = document.createElement("div");
      newHeader.className = "api-example-header api-example-header-auto";
      newHeader.appendChild(switcherHtml);
      example.insertBefore(newHeader, example.firstChild);
    }

    // Prepare content versions
    // Display: password always shows as <YOUR_PASSWORD> (user must replace manually)
    const privateMaskedContent = originalContent
      .replace(/YOUR_TOKEN/g, maskedToken)
      .replace(/your-api-key/gi, maskedToken)
      .replace(/sk_live_xxxxxxxxxxxxxxxxxxxx/g, maskedToken)
      .replace(/your_username/g, actualUsername)
      .replace(/your_password/g, passwordPlaceholder);

    // Copy: same as display (password as placeholder)
    const privateActualContent = originalContent
      .replace(/YOUR_TOKEN/g, actualToken)
      .replace(/your-api-key/gi, actualToken)
      .replace(/sk_live_xxxxxxxxxxxxxxxxxxxx/g, actualToken)
      .replace(/your_username/g, actualUsername)
      .replace(/your_password/g, passwordPlaceholder);

    // State tracking
    let currentMode = "general";
    let isTokenVisible = false;

    // Store actual content for copy functionality
    (example as HTMLElement).dataset.copyContent = originalContent;

    const eyeToggle = switcherHtml.querySelector(".eye-toggle") as HTMLElement;
    const eyeIcon = eyeToggle?.querySelector("i");

    // Mode switcher buttons
    switcherHtml
      .querySelectorAll(".env-btn:not(.eye-toggle)")
      .forEach((btn) => {
        btn.addEventListener("click", function (this: HTMLElement) {
          const mode = this.dataset.mode;
          currentMode = mode || "general";

          // Update active state
          switcherHtml
            .querySelectorAll(".env-btn:not(.eye-toggle)")
            .forEach((b) => b.classList.remove("active"));
          this.classList.add("active");

          // Enable/disable eye toggle based on mode (always visible for consistent layout)
          if (eyeToggle) {
            if (mode === "private") {
              eyeToggle.classList.remove("disabled");
              eyeToggle.title = "Toggle token visibility";
            } else {
              eyeToggle.classList.add("disabled");
              eyeToggle.title =
                "Toggle token visibility (enable Private mode first)";
            }
          }

          // Reset visibility when switching modes
          isTokenVisible = false;
          if (eyeIcon) {
            eyeIcon.className = "fas fa-eye-slash";
          }

          // Update code content
          if (mode === "general") {
            codeBlock.textContent = originalContent;
            (example as HTMLElement).dataset.copyContent = originalContent;
          } else {
            codeBlock.textContent = privateMaskedContent;
            (example as HTMLElement).dataset.copyContent = privateActualContent;
          }
        });
      });

    // Eye toggle for visibility (only works in Private mode)
    if (eyeToggle) {
      eyeToggle.addEventListener("click", () => {
        // Ignore click if disabled (General mode)
        if (eyeToggle.classList.contains("disabled")) return;

        isTokenVisible = !isTokenVisible;

        if (eyeIcon) {
          eyeIcon.className = isTokenVisible
            ? "fas fa-eye"
            : "fas fa-eye-slash";
        }

        if (currentMode === "private") {
          codeBlock.textContent = isTokenVisible
            ? privateActualContent
            : privateMaskedContent;
        }
      });
    }
  });
}

/**
 * Escape special regex characters
 */
function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Setup download dropdown toggle
 */
function setupDownloadDropdown(): void {
  const btn = document.getElementById("download-btn");
  const menu = document.getElementById("download-menu");

  if (btn && menu) {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      menu.classList.toggle("show");
    });

    document.addEventListener("click", () => {
      menu.classList.remove("show");
    });
  }
}

/**
 * Setup example-specific tabs (Generic vs Campaign Token)
 */
function setupExampleTabs(): void {
  document.querySelectorAll(".api-example-tab").forEach((tab) => {
    tab.addEventListener("click", function (this: HTMLElement) {
      const panelId = this.dataset.panel;
      if (!panelId) return;

      const example = this.closest(".api-example");
      if (!example) return;

      example
        .querySelectorAll(".api-example-tab")
        .forEach((t) => t.classList.remove("active"));
      this.classList.add("active");

      example
        .querySelectorAll(".api-example-panel")
        .forEach((p) => p.classList.remove("active"));
      const targetPanel = document.getElementById(panelId);
      if (targetPanel) {
        targetPanel.classList.add("active");
      }
    });
  });
}

/**
 * Setup tab switching functionality
 */
function setupTabs(): void {
  document.querySelectorAll(".api-tab").forEach((tab) => {
    tab.addEventListener("click", function (this: HTMLElement) {
      const tabId = this.dataset.tab;
      if (!tabId) return;

      const parent = this.closest(".api-section");
      if (!parent) return;

      parent
        .querySelectorAll(".api-tab")
        .forEach((t) => t.classList.remove("active"));
      this.classList.add("active");

      parent
        .querySelectorAll(".api-tab-content")
        .forEach((c) => c.classList.remove("active"));
      const targetContent = document.getElementById(tabId);
      if (targetContent) {
        targetContent.classList.add("active");
      }
    });
  });
}

/**
 * Setup copy to clipboard buttons
 * Uses dataset.copyContent if available (for masked private mode - copies actual token)
 */
function setupCopyButtons(): void {
  document.querySelectorAll(".copy-btn").forEach((btn) => {
    btn.addEventListener("click", function (this: HTMLElement) {
      const targetId = this.dataset.copy;
      if (!targetId) return;

      const target = document.getElementById(targetId);
      if (!target) return;

      // Check if parent example has copyContent (for private mode with actual token)
      const example = target.closest(".api-example") as HTMLElement | null;

      // Explicitly check for non-empty string (empty string is falsy)
      const copyContent =
        example?.dataset.copyContent && example.dataset.copyContent.length > 0
          ? example.dataset.copyContent
          : target.textContent || "";

      if (copyContent) {
        navigator.clipboard.writeText(copyContent).then(() => {
          const icon = this.querySelector("i");
          if (icon) {
            icon.className = "fas fa-check";
            setTimeout(() => {
              icon.className = "fas fa-copy";
            }, 2000);
          }
        });
      }
    });
  });
}

/**
 * Setup smooth scroll for sidebar anchor links
 */
function setupSmoothScroll(): void {
  document.querySelectorAll(".api-nav a.subsection-link").forEach((link) => {
    link.addEventListener(
      "click",
      function (this: HTMLAnchorElement, e: Event) {
        const href = this.getAttribute("href");
        if (!href || !href.startsWith("#")) return;

        e.preventDefault();
        const target = document.querySelector(href);
        if (target) {
          target.scrollIntoView({ behavior: "smooth", block: "start" });
          history.pushState(null, "", href);
          document
            .querySelectorAll(".api-nav a.subsection-link")
            .forEach((l) => l.classList.remove("active"));
          this.classList.add("active");
        }
      },
    );
  });
}

/**
 * Setup intersection observer for sidebar highlighting
 */
function setupSectionObserver(): void {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const id = entry.target.id;
          document
            .querySelectorAll(".api-nav a.subsection-link")
            .forEach((link) => {
              const href = link.getAttribute("href");
              const dataTarget = link.getAttribute("data-target");
              const isActive = href === "#" + id || dataTarget === id;
              link.classList.toggle("active", isActive);
            });
        }
      });
    },
    { threshold: 0.1, rootMargin: "-120px 0px -60% 0px" },
  );

  document.querySelectorAll(".api-section[id]").forEach((section) => {
    observer.observe(section);
  });

  if (window.location.hash) {
    const hash = window.location.hash.substring(1);
    document.querySelectorAll(".api-nav a.subsection-link").forEach((link) => {
      const dataTarget = link.getAttribute("data-target");
      link.classList.toggle("active", dataTarget === hash);
    });
  }
}

/**
 * Setup collapsible internal API group in sidebar
 */
function setupInternalToggle(): void {
  document.querySelectorAll(".api-nav-group-toggle").forEach((btn) => {
    btn.addEventListener("click", function (this: HTMLElement) {
      const isExpanded = this.classList.toggle("expanded");
      this.setAttribute("aria-expanded", String(isExpanded));
      const items = this.nextElementSibling as HTMLElement | null;
      if (items) {
        items.classList.toggle("expanded", isExpanded);
      }
    });
  });
}

/**
 * Setup info card switchers
 */
function setupCardSwitchers(): void {
  document.querySelectorAll(".api-info-card-switchable").forEach((card) => {
    const switchBtns = card.querySelectorAll(".switch-btn");
    const valueEl = card.querySelector(".api-switchable-value");

    switchBtns.forEach((btn) => {
      btn.addEventListener("click", function (this: HTMLElement) {
        const value = this.dataset.value;
        if (!value || !valueEl) return;

        switchBtns.forEach((b) => b.classList.remove("active"));
        this.classList.add("active");

        const newValue = valueEl.getAttribute(`data-${value}`);
        if (newValue) {
          valueEl.textContent = newValue;
        }
      });
    });
  });

  document.querySelectorAll(".copy-btn-mini").forEach((btn) => {
    btn.addEventListener("click", function (this: HTMLElement) {
      const card = this.closest(".api-info-card-switchable");
      const valueEl = card?.querySelector(".api-switchable-value");
      if (valueEl && valueEl.textContent) {
        navigator.clipboard.writeText(valueEl.textContent).then(() => {
          this.classList.add("copied");
          const icon = this.querySelector("i");
          if (icon) {
            icon.className = "fas fa-check";
            setTimeout(() => {
              icon.className = "fas fa-copy";
              this.classList.remove("copied");
            }, 2000);
          }
        });
      }
    });
  });
}

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", initApiDocs);
