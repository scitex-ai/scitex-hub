// Reset BibTeX form to initial state
function resetBibtexForm() {
  document.getElementById("bibtexFormArea").style.display = "block";
  document.getElementById("bibtexProgressArea").style.display = "none";
  document.getElementById("bibtexEnrichmentForm").reset();
}

document.addEventListener("DOMContentLoaded", function () {
  // BibTeX AJAX Form Submission
  const bibtexForm = document.getElementById("bibtexEnrichmentForm");
  const fileInput = document.getElementById("bibtexFileInput");
  const dropZone = document.getElementById("dropZone");

  if (bibtexForm) {
    // Drag & Drop functionality with drag counter
    if (dropZone && fileInput) {
      let dragCounter = 0;

      ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
        dropZone.addEventListener(eventName, preventDefaults, false);
      });

      function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
      }

      // Dragenter: increment counter and apply styles
      dropZone.addEventListener("dragenter", (e) => {
        dragCounter++;
        if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
        dropZone.style.borderColor = "#6B8FB3";
        dropZone.style.borderStyle = "solid";
        dropZone.style.background = "rgba(107, 143, 179, 0.15)";
        dropZone.style.transform = "scale(1.01)";
        dropZone.style.boxShadow = "0 4px 16px rgba(107, 143, 179, 0.3)";
      });

      // Dragover: maintain styles
      dropZone.addEventListener("dragover", (e) => {
        if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
      });

      // Dragleave: decrement counter, remove styles only when truly leaving
      dropZone.addEventListener("dragleave", (e) => {
        dragCounter--;
        if (dragCounter === 0) {
          dropZone.style.borderColor = "var(--scitex-color-03)";
          dropZone.style.borderStyle = "dashed";
          dropZone.style.background = "var(--color-canvas-subtle)";
          dropZone.style.transform = "scale(1)";
          dropZone.style.boxShadow = "none";
        }
      });

      // Drop: reset counter and remove styles
      dropZone.addEventListener("drop", (e) => {
        dragCounter = 0;
        dropZone.style.borderColor = "var(--scitex-color-03)";
        dropZone.style.borderStyle = "dashed";
        dropZone.style.background = "var(--color-canvas-subtle)";
        dropZone.style.transform = "scale(1)";
        dropZone.style.boxShadow = "none";
      });

      // Handle dropped files
      dropZone.addEventListener("drop", function (e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0) {
          const file = files[0];
          if (file.name.endsWith(".bib")) {
            // Assign the dropped file to the input
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            fileInput.files = dataTransfer.files;

            // Update visual feedback
            showFileName(file.name);
          } else {
            alert("Please drop a .bib file");
          }
        }
      });

      // Handle file input change (click to upload)
      fileInput.addEventListener("change", function (e) {
        if (this.files.length > 0) {
          showFileName(this.files[0].name);
        }
      });

      // Function to display file name and auto-submit
      function showFileName(fileName) {
        document.getElementById("uploadMessage").style.display = "none";
        document.getElementById("fileNameDisplay").style.display = "block";
        document.getElementById("fileName").textContent = fileName;

        // Add success visual feedback to drop zone
        dropZone.style.borderColor = "var(--info-color)";
        dropZone.style.background = "rgba(107, 143, 179, 0.1)";

        // Auto-submit after short delay
        setTimeout(() => {
          autoSubmitBibtexForm();
        }, 300);
      }

      // Auto-submit function
      function autoSubmitBibtexForm() {
        const formData = new FormData(bibtexForm);

        // Get CSRF token
        const csrfToken = document.querySelector(
          "[name=csrfmiddlewaretoken]",
        ).value;

        // Show processing state
        dropZone.style.borderColor = "var(--info-color)";
        dropZone.style.background = "rgba(107, 143, 179, 0.15)";

        // Show progress area (but keep form visible - just collapse dropzone)
        document.getElementById("bibtexProgressArea").style.display = "block";

        // Submit form via AJAX
        fetch(window.SCHOLAR_CONFIG.urls.bibtexUpload, {
          method: "POST",
          body: formData,
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": csrfToken,
          },
        })
          .then((response) => {
            if (response.status === 409) {
              // Conflict - user already has a job in progress
              return response.json().then((data) => {
                if (data.requires_confirmation && data.existing_job) {
                  // Ask user if they want to cancel the existing job
                  const msg = `You already have a job in progress: "${data.existing_job.filename}" (${data.existing_job.progress}% complete).\n\nCancel it and start a new job?`;
                  if (confirm(msg)) {
                    // Resubmit with force flag
                    formData.append("force", "true");
                    return fetch(window.SCHOLAR_CONFIG.urls.bibtexUpload, {
                      method: "POST",
                      body: formData,
                      headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "X-CSRFToken": csrfToken,
                      },
                    }).then((r) => r.json());
                  } else {
                    // User declined, start monitoring existing job
                    if (data.existing_job.id) {
                      pollBibtexJobStatus(data.existing_job.id);
                    }
                    throw new Error("User declined to cancel existing job");
                  }
                } else {
                  alert(
                    data.message ||
                      "You already have a job in progress. Please wait for it to complete.",
                  );
                  resetBibtexForm();
                  throw new Error("Job already running");
                }
              });
            }
            return response.json();
          })
          .then((data) => {
            if (data.success && data.job_id) {
              // Start polling for job status
              pollBibtexJobStatus(data.job_id);
            } else {
              alert("Error: " + (data.error || "Failed to start enrichment"));
              resetBibtexForm();
            }
          })
          .catch((error) => {
            const ignoredErrors = [
              "Job already running",
              "User declined to cancel existing job",
            ];
            if (!ignoredErrors.includes(error.message)) {
              console.error("Error:", error);
              alert("Failed to upload BibTeX file: " + error.message);
              resetBibtexForm();
            }
          });
      }
    }

    // Prevent manual form submission (auto-processing only)
    bibtexForm.addEventListener("submit", function (e) {
      e.preventDefault();
    });
  }

  // Simple search functionality - using let to avoid redeclaration errors
  let searchForm = document.querySelector("form");
  let searchInput = document.querySelector('input[name="q"]');
  let searchButton = document.getElementById("searchButton");
  let progressiveLoadingStatus = document.getElementById(
    "progressiveLoadingStatus",
  );
  let progressiveResults = document.getElementById("progressiveResults");

  // Advanced filters functionality
  const toggleAdvancedFilters = document.getElementById(
    "toggleAdvancedFilters",
  );
  const advancedFilters = document.getElementById("advancedFilters");
  const clearFiltersBtn = document.getElementById("clearFilters");
  const saveSearchBtn = document.getElementById("saveSearch");

  // Toggle advanced filters
  if (toggleAdvancedFilters) {
    toggleAdvancedFilters.addEventListener("click", function () {
      if (advancedFilters.style.display === "none") {
        advancedFilters.style.display = "block";
        this.innerHTML =
          '<i class="fas fa-sliders-h"></i> Hide Advanced Filters';
        this.style.backgroundColor = "var(--primary-color, #1a2332)";
        this.style.color = "white";
        this.style.borderColor = "var(--primary-color, #1a2332)";
      } else {
        advancedFilters.style.display = "none";
        this.innerHTML = '<i class="fas fa-sliders-h"></i> Advanced Filters';
        this.style.backgroundColor = "transparent";
        this.style.color = "var(--primary-color, #1a2332)";
        this.style.borderColor = "var(--primary-color, #1a2332)";
      }
    });
  }

  // Clear all filters
  if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener("click", function () {
      // Reset all filter inputs
      document
        .querySelectorAll("#advancedFilters input, #advancedFilters select")
        .forEach((input) => {
          if (input.type === "checkbox" || input.type === "radio") {
            input.checked = false;
          } else {
            input.value = "";
          }
        });

      // Reset basic filters
      document
        .querySelectorAll('#basicFilters input[type="checkbox"]')
        .forEach((input) => {
          input.checked = false;
        });

      // Reset source toggles to all enabled
      document.querySelectorAll(".source-toggle").forEach((toggle) => {
        toggle.checked = true;
      });
      saveSourcePreferences();

      updateActiveFilterCount();
    });
  }

  // Save search functionality
  if (saveSearchBtn) {
    saveSearchBtn.addEventListener("click", function () {
      const query = searchInput.value.trim();
      // Allow saving with empty query - the backend will handle validation if needed
      // if (!query) {
      //     alert('Please enter a search query first.');
      //     return;
      // }

      const searchName = prompt(
        "Enter a name for this saved search:",
        query.substring(0, 50),
      );
      if (!searchName) return;

      // Collect all active filters
      const filters = {};
      document
        .querySelectorAll(
          '#advancedFilters input, #advancedFilters select, #basicFilters input[type="checkbox"]:checked',
        )
        .forEach((input) => {
          if (input.name && input.value) {
            filters[input.name] = input.value;
          }
        });

      // Save to backend
      fetch("/scholar/api/save-search/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({
          name: searchName,
          query: query,
          filters: filters,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "success") {
            alert("Search saved successfully!");
          } else {
            alert(data.message || "Error saving search");
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          alert("Error saving search. Please try again.");
        });
    });
  }

  // Update active filter count
  function updateActiveFilterCount() {
    let count = 0;

    // Count advanced filters
    document
      .querySelectorAll("#advancedFilters input, #advancedFilters select")
      .forEach((input) => {
        if (
          input.name &&
          input.value &&
          ((input.type === "checkbox" && input.checked) ||
            (input.type !== "checkbox" && input.type !== "radio"))
        ) {
          count++;
        }
      });

    // Count basic filters and source toggles
    document
      .querySelectorAll(
        '#basicFilters input[type="checkbox"]:checked:not(.source-toggle)',
      )
      .forEach(() => count++);

    // Count enabled sources (only count as filter if not all sources are enabled)
    const totalSources = document.querySelectorAll(".source-toggle").length;
    const enabledSources = document.querySelectorAll(
      ".source-toggle:checked",
    ).length;
    if (enabledSources < totalSources && enabledSources > 0) {
      count++; // Count as one filter if source selection is customized
    }

    const activeFilterCountEl = document.getElementById("activeFilterCount");
    if (activeFilterCountEl) {
      activeFilterCountEl.textContent = count;
    }
  }

  // Source preference management with database/localStorage
  function saveSourcePreferences() {
    const preferences = {};
    document.querySelectorAll(".source-toggle").forEach((toggle) => {
      preferences[toggle.value] = toggle.checked;
    });

    // Save to database if user is logged in, otherwise use localStorage
    if (
      window.scholarConfig &&
      window.scholarConfig.user &&
      window.scholarConfig.user.isAuthenticated
    ) {
      fetch("/scholar/api/preferences/sources/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({ sources: preferences }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "success") {
            console.log("Source preferences saved to profile");
          }
        })
        .catch((error) => console.error("Error saving preferences:", error));
    } else {
      // For visitor users, use localStorage
      localStorage.setItem(
        "scholar_source_preferences",
        JSON.stringify(preferences),
      );
    }
  }

  function getCsrfToken() {
    return (
      document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
      document
        .querySelector('meta[name="csrf-token"]')
        ?.getAttribute("content") ||
      getCookie("csrftoken")
    );
  }

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
  }

  // Update source display text based on selected checkboxes
  function updateSourceDisplay() {
    const selectedSources = document.querySelectorAll(".source-toggle:checked");
    const sourceDisplay = document.getElementById("sourceDisplay");

    if (sourceDisplay) {
      const sourceNames = [];
      selectedSources.forEach((checkbox) => {
        switch (checkbox.value) {
          case "pubmed":
            sourceNames.push("PubMed");
            break;
          case "google_scholar":
            sourceNames.push("Google Scholar");
            break;
          case "arxiv":
            sourceNames.push("arXiv");
            break;
          case "semantic":
            sourceNames.push("Semantic Scholar");
            break;
        }
      });

      let displayText = "";
      if (sourceNames.length === 0) {
        displayText =
          "from no sources selected (ERROR: please select at least one source)";
      } else if (sourceNames.length === 4) {
        displayText =
          "from all external sources: PubMed, Google Scholar, arXiv, Semantic Scholar + SciTeX Index";
      } else if (sourceNames.length === 1) {
        displayText = `from ${sourceNames[0]} + SciTeX Index`;
      } else {
        displayText = `from ${sourceNames.join(", ")} + SciTeX Index`;
      }

      sourceDisplay.textContent = displayText;
    }
  }

  function loadSourcePreferences() {
    if (
      window.scholarConfig &&
      window.scholarConfig.user &&
      window.scholarConfig.user.isAuthenticated
    ) {
      // Load from database for logged-in users
      fetch("/scholar/api/preferences/")
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "success" && data.preferences.preferred_sources) {
            const preferences = data.preferences.preferred_sources;
            applySourcePreferences(preferences);
          } else {
            // No saved preferences, set defaults
            setDefaultSourcePreferences();
          }
        })
        .catch((error) => {
          console.log(
            "Could not load user preferences, using localStorage fallback",
          );
          // Fallback to localStorage if database fails
          loadSourcePreferencesFromStorage();
        });
    } else {
      // Load from localStorage for visitor users
      loadSourcePreferencesFromStorage();
    }
  }

  function loadSourcePreferencesFromStorage() {
    const saved = localStorage.getItem("scholar_source_preferences");
    if (saved) {
      try {
        const preferences = JSON.parse(saved);
        applySourcePreferences(preferences);
      } catch (e) {
        console.log("Could not load source preferences from localStorage");
        setDefaultSourcePreferences();
      }
    } else {
      // No saved preferences, set defaults
      setDefaultSourcePreferences();
    }
  }

  function applySourcePreferences(preferences) {
    let hasAnyPreference = false;
    document.querySelectorAll(".source-toggle").forEach((toggle) => {
      if (preferences.hasOwnProperty(toggle.value)) {
        toggle.checked = preferences[toggle.value];
        hasAnyPreference = true;
      }
    });

    // If no preferences found, set defaults
    if (!hasAnyPreference) {
      setDefaultSourcePreferences();
    }

    // Update master toggle after applying preferences
    updateAllSourcesToggle();
    updateSourceDisplay();
    updateActiveFilterCount();
  }

  function setDefaultSourcePreferences() {
    // Default: All sources enabled
    document.querySelectorAll(".source-toggle").forEach((toggle) => {
      toggle.checked = true;
    });
    updateAllSourcesToggle();
    updateSourceDisplay();
    updateActiveFilterCount();
  }

  // Enhanced source toggle logic with "All Sources" master toggle
  function initializeSourceToggles() {
    const allSourcesToggle = document.getElementById("source_all_toggle");
    const sourceToggles = document.querySelectorAll(".source-toggle");

    // Master "All Sources" toggle functionality
    if (allSourcesToggle) {
      allSourcesToggle.addEventListener("change", function () {
        const isChecked = this.checked;
        // Set all individual source toggles to match
        sourceToggles.forEach((toggle) => {
          toggle.checked = isChecked;
        });
        handleSourceChange();
      });
    }

    // Individual source toggle functionality
    sourceToggles.forEach((toggle) => {
      toggle.addEventListener("change", function () {
        // Update "All Sources" toggle based on individual selections
        updateAllSourcesToggle();
        handleSourceChange();
      });
    });

    // Initial state check
    updateAllSourcesToggle();
  }

  function updateAllSourcesToggle() {
    const allSourcesToggle = document.getElementById("source_all_toggle");
    const sourceToggles = document.querySelectorAll(".source-toggle");
    const checkedToggles = document.querySelectorAll(".source-toggle:checked");

    if (allSourcesToggle) {
      if (checkedToggles.length === sourceToggles.length) {
        // All individual sources are checked
        allSourcesToggle.checked = true;
        allSourcesToggle.indeterminate = false;
      } else if (checkedToggles.length === 0) {
        // No individual sources are checked
        allSourcesToggle.checked = false;
        allSourcesToggle.indeterminate = false;
      } else {
        // Some but not all individual sources are checked
        allSourcesToggle.checked = false;
        allSourcesToggle.indeterminate = true;
      }
    }
  }

  function handleSourceChange() {
    saveSourcePreferences();
    updateActiveFilterCount();
    updateSourceDisplay();

    // Auto-submit search if there's a query
    const searchInput = document.querySelector('input[name="q"]');
    if (searchInput && searchInput.value.trim()) {
      const autoSubmitForm = document.querySelector("form");
      if (autoSubmitForm) {
        autoSubmitForm.submit();
      }
    }
  }

  // Initialize source toggles
  initializeSourceToggles();

  // Load source preferences on page load - ensure they persist
  loadSourcePreferences();

  // Force reload preferences after a brief delay to ensure DOM is ready
  setTimeout(() => {
    loadSourcePreferences();
  }, 200);

  // Monitor filter changes
  document
    .querySelectorAll(
      "#advancedFilters input, #advancedFilters select, #basicFilters input",
    )
    .forEach((input) => {
      input.addEventListener("change", updateActiveFilterCount);
      input.addEventListener("input", updateActiveFilterCount);
    });

  // Initial filter count and source display
  updateActiveFilterCount();
  updateSourceDisplay();

  // Auto-submit on filter changes
  document
    .querySelectorAll(
      '#basicFilters input[type="checkbox"]:not(.source-toggle)',
    )
    .forEach((input) => {
      input.addEventListener("change", function () {
        if (searchInput.value.trim()) {
          form.submit();
        }
      });
    });

  // Sort functionality - avoid redeclaration errors
  if (!window._scholarSortInitialized) {
    const sortSelect = document.getElementById("sortSelect");
    if (sortSelect && !sortSelect._listenerAttached) {
      sortSelect.addEventListener("change", function () {
        const currentUrl = new URL(window.location.href);
        currentUrl.searchParams.set("sort_by", this.value);
        window.location.href = currentUrl.toString();
      });
      sortSelect._listenerAttached = true;
    }
    window._scholarSortInitialized = true;
  }

  // Progressive search is always available

  // Helper function to reset all progress indicators
  function resetProgressIndicators() {
    document.querySelectorAll(".progress-source").forEach((source) => {
      const badge = source.querySelector(".badge");
      const spinner = source.querySelector(".spinner-border");
      const count = source.querySelector(".count");

      if (badge) badge.className = "badge bg-light";
      if (spinner) spinner.style.display = "none";
      if (count) count.textContent = "-";
    });
  }

  // Search functionality - intercept form submission for progressive search
  const literatureSearchForm = document.getElementById("literatureSearchForm");
  // searchButton already declared above at line 1101

  // Search functionality - intercept form submission for progressive search
  if (literatureSearchForm) {
    literatureSearchForm.addEventListener("submit", function (e) {
      e.preventDefault(); // Prevent normal form submission

      const query = searchInput.value.trim();
      // Allow search without explicit query (could be filtering existing results)
      // if (!query) {
      //     alert('Please enter a search query.');
      //     return;
      // }

      // Save current source preferences before starting search
      saveSourcePreferences();

      // Hide regular results and show progressive interface
      const regularResults = document.querySelectorAll(".result-card");
      regularResults.forEach((card) => (card.style.display = "none"));

      // Show progressive interface
      if (progressiveLoadingStatus)
        progressiveLoadingStatus.style.display = "block";
      if (progressiveResults) {
        progressiveResults.style.display = "block";
        progressiveResults.innerHTML = "";
      }

      // Reset progress indicators
      document.querySelectorAll(".progress-source").forEach((source) => {
        const badge = source.querySelector(".badge");
        const spinner = source.querySelector(".spinner-border");
        const count = source.querySelector(".count");

        if (badge) badge.className = "badge bg-secondary";
        if (spinner) spinner.style.display = "inline-block";
        if (count) count.textContent = "0";
      });

      // Start progressive search
      // DISABLED: Now using SciTeX search instead (see scitex-search.js)
      // startProgressiveSearch(query);
    });
  }

  // Progressive search implementation
  function startProgressiveSearch(query) {
    // Get selected sources from checkboxes
    const selectedCheckboxes = document.querySelectorAll(
      ".source-toggle:checked",
    );
    const selectedSourceValues = Array.from(selectedCheckboxes).map(
      (cb) => cb.value,
    );

    const allSources = [
      {
        name: "pubmed",
        value: "pubmed",
        endpoint: "/scholar/api/search/pubmed/",
        maxResults: 50,
      },
      {
        name: "google_scholar",
        value: "google_scholar",
        endpoint: "/scholar/api/search/google-scholar/",
        maxResults: 50,
      },
      {
        name: "arxiv",
        value: "arxiv",
        endpoint: "/scholar/api/search/arxiv/",
        maxResults: 50,
      },
      {
        name: "semantic",
        value: "semantic",
        endpoint: "/scholar/api/search/semantic/",
        maxResults: 25,
      },
    ];

    // Filter to only selected sources
    const sourcesToSearch = allSources.filter((source) =>
      selectedSourceValues.includes(source.value),
    );

    if (sourcesToSearch.length === 0) {
      alert("Please select at least one search source.");
      resetProgressIndicators();
      return;
    }

    // Search each selected source in parallel
    sourcesToSearch.forEach((source) => {
      searchSource(source, query);
    });

    // Reset progress indicators for unselected sources
    allSources.forEach((source) => {
      const shouldSearch = selectedSourceValues.includes(source.value);
      if (!shouldSearch) {
        const progressSource = document.querySelector(
          `[data-source="${source.name}"]`,
        );
        if (progressSource) {
          const badge = progressSource.querySelector(".badge");
          const spinner = progressSource.querySelector(".spinner-border");
          const count = progressSource.querySelector(".count");

          if (badge) badge.className = "badge bg-light";
          if (spinner) spinner.style.display = "none";
          if (count) count.textContent = "-";
        }
      }
    });
  }

  function searchSource(source, query) {
    const url = `${source.endpoint}?q=${encodeURIComponent(query)}&max_results=${source.maxResults}`;
    const progressSource = document.querySelector(
      `[data-source="${source.name}"]`,
    );

    fetch(url)
      .then((response) => response.json())
      .then((data) => {
        if (data.status === "success") {
          // Update progress indicator
          if (progressSource) {
            const badge = progressSource.querySelector(".badge");
            const spinner = progressSource.querySelector(".spinner-border");
            const count = progressSource.querySelector(".count");

            if (badge) badge.className = "badge bg-success";
            if (spinner) spinner.style.display = "none";
            if (count) count.textContent = data.count;
          }

          // Add results to progressive container
          data.results.forEach((result) => {
            addResultToProgressive(result);
          });
        } else {
          // Handle error
          handleSearchError(source.name, data.error || "Unknown error");
        }
      })
      .catch((error) => {
        handleSearchError(source.name, error.message);
      });
  }

  function addResultToProgressive(result) {
    if (!progressiveResults) {
      console.warn("Progressive results container not found");
      return;
    }

    const resultCard = createResultCard(result);
    progressiveResults.appendChild(resultCard);

    // Animate the new result
    resultCard.style.opacity = "0";
    resultCard.style.transform = "translateY(20px)";
    setTimeout(() => {
      resultCard.style.transition = "all 0.3s ease";
      resultCard.style.opacity = "1";
      resultCard.style.transform = "translateY(0)";
    }, 50);
  }

  function createResultCard(result) {
    const cardDiv = document.createElement("div");
    cardDiv.className = "result-card";
    cardDiv.setAttribute("data-paper-id", result.id || "");
    cardDiv.setAttribute("data-title", result.title || "");
    cardDiv.setAttribute("data-authors", result.authors || "");
    cardDiv.setAttribute("data-year", result.year || "");
    cardDiv.setAttribute("data-journal", result.journal || "Unknown Journal");

    cardDiv.innerHTML = `
            <h6 class="result-title">
                <a href="#" class="text-decoration-none">
                    ${result.title || "Unknown Title"}
                </a>
            </h6>
            <div class="result-authors">
                ${result.authors || "Unknown Authors"}
            </div>
            <div class="d-flex align-items-center mt-2 flex-wrap">
                <span class="year-badge me-2">${result.year || "2024"}</span>
                ${result.is_open_access ? '<span class="open-access me-2">Open Access</span>' : ""}
                ${result.impact_factor ? `<span class="badge bg-warning text-dark me-2" style="font-size: 0.7rem;">IF: ${result.impact_factor}</span>` : ""}
                <small class="text-muted">
                    ${result.journal || "Unknown Journal"}
                    ${result.citations && result.citations > 0 ? `• <strong>${result.citations} citations</strong>` : ""}
                    ${result.pmid ? `• PMID: ${result.pmid}` : ""}
                </small>
                ${result.source ? `<span class="badge bg-info ms-2" style="font-size: 0.7rem;">${result.source.toUpperCase()}</span>` : ""}
            </div>
            <div class="result-snippet mt-2">
                <div class="abstract-preview">
                    ${
                      result.abstract && result.abstract.length > 200
                        ? `<span class="abstract-short">${result.abstract.substring(0, 200)}...</span>
                         <span class="abstract-full" style="display: none;">${result.abstract}</span>
                         <a href="#" class="abstract-toggle text-primary ms-2" style="font-size: 0.9rem;">[Show full abstract]</a>`
                        : result.abstract || "No abstract available."
                    }
                </div>
            </div>
            <div class="mt-3">
                ${
                  result.pdf_url
                    ? `<a href="${result.pdf_url}" class="btn btn-outline-success btn-sm me-2" target="_blank">📄 Download PDF</a>`
                    : '<span class="btn btn-outline-secondary btn-sm me-2 disabled">📄 No PDF</span>'
                }
                <div class="btn-group" role="group">
                    <button type="button" class="btn btn-outline-info btn-sm dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false">
                        📝 Export Citation
                    </button>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="#" onclick="exportCitation(this, 'bibtex')">
                            <i class="fas fa-file-code"></i> BibTeX (.bib)
                        </a></li>
                        <li><a class="dropdown-item" href="#" onclick="exportCitation(this, 'ris')">
                            <i class="fas fa-file-text"></i> RIS (.ris)
                        </a></li>
                        <li><a class="dropdown-item" href="#" onclick="exportCitation(this, 'endnote')">
                            <i class="fas fa-file-alt"></i> EndNote (.enw)
                        </a></li>
                        <li><a class="dropdown-item" href="#" onclick="exportCitation(this, 'csv')">
                            <i class="fas fa-table"></i> CSV (.csv)
                        </a></li>
                        <li><hr class="dropdown-divider"></li>
                        <li><a class="dropdown-item" href="#" onclick="showBibTeX(this)">
                            <i class="fas fa-eye"></i> Quick Preview
                        </a></li>
                    </ul>
                </div>
                <a href="#" class="btn btn-outline-warning btn-sm me-2" onclick="saveToLibrary(this)">
                    ⭐ Add to Library
                </a>
            </div>
        `;

    // Add event listeners for abstract toggle
    const abstractToggle = cardDiv.querySelector(".abstract-toggle");
    if (abstractToggle) {
      abstractToggle.addEventListener("click", function (e) {
        e.preventDefault();
        const abstractPreview = this.closest(".abstract-preview");
        const shortAbstract = abstractPreview.querySelector(".abstract-short");
        const fullAbstract = abstractPreview.querySelector(".abstract-full");

        if (fullAbstract.style.display === "none") {
          shortAbstract.style.display = "none";
          fullAbstract.style.display = "inline";
          this.textContent = "[Show less]";
        } else {
          shortAbstract.style.display = "inline";
          fullAbstract.style.display = "none";
          this.textContent = "[Show full abstract]";
        }
      });
    }

    return cardDiv;
  }

  function handleSearchError(sourceName, errorMessage) {
    const progressSource = document.querySelector(
      `[data-source="${sourceName}"]`,
    );
    if (!progressSource) {
      console.error(
        `${sourceName} search failed (no progress element):`,
        errorMessage,
      );
      return;
    }

    const badge = progressSource.querySelector(".badge");
    const spinner = progressSource.querySelector(".spinner-border");
    const count = progressSource.querySelector(".count");

    if (badge) badge.className = "badge bg-danger";
    if (spinner) spinner.style.display = "none";
    if (count) count.textContent = "Error";

    console.error(`${sourceName} search failed:`, errorMessage);
  }

  // Auto-submit when project filter changes (but not sort)
  document.querySelectorAll('select[name="project"]').forEach((select) => {
    select.addEventListener("change", function () {
      if (searchInput.value.trim()) {
        form.submit();
      }
    });
  });

  // Handle sort functionality - sortSelect already declared above at line 1482
  // The sortSelect event listener is already registered at line 1482-1489

  // Note: Source selection auto-submit is now handled by the source-toggle event listeners above

  // Note: Bulk export functionality removed - papers can be added to library instead

  // Handle abstract toggle functionality
  document.querySelectorAll(".abstract-toggle").forEach((toggle) => {
    toggle.addEventListener("click", function (e) {
      e.preventDefault();
      const abstractPreview = this.closest(".abstract-preview");
      const shortAbstract = abstractPreview.querySelector(".abstract-short");
      const fullAbstract = abstractPreview.querySelector(".abstract-full");

      if (fullAbstract.style.display === "none") {
        // Show full abstract
        shortAbstract.style.display = "none";
        fullAbstract.style.display = "inline";
        this.textContent = "[Show less]";
      } else {
        // Show short abstract
        shortAbstract.style.display = "inline";
        fullAbstract.style.display = "none";
        this.textContent = "[Show full abstract]";
      }
    });
  });

  // Save Search functionality
  const saveSearchButton = document.getElementById("saveSearch");
  if (saveSearchButton) {
    saveSearchButton.addEventListener("click", function () {
      const saveSearchFormElement = document.getElementById(
        "literatureSearchForm",
      );
      const formData = new FormData(saveSearchFormElement);

      // Get current search query - allow empty query
      const query = formData.get("q");
      // Allow saving search with empty query
      // if (!query || !query.trim()) {
      //     alert('Please enter a search query first');
      //     return;
      // }

      // Get search name from user
      const searchName = prompt(
        "Enter a name for this saved search:",
        query.substring(0, 50),
      );
      if (!searchName) return;

      // Collect all active filters
      const filters = {};
      formData.forEach((value, key) => {
        if (value && key !== "q") {
          filters[key] = value;
        }
      });

      // Send save request
      fetch("/scholar/api/save-search/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({
          name: searchName,
          query: query.trim(),
          filters: filters,
          email_alerts: false,
          alert_frequency: "never",
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status === "success") {
            alert("Search saved successfully!");
          } else {
            alert("Error saving search: " + (data.message || "Unknown error"));
          }
        })
        .catch((error) => {
          console.error("Error:", error);
          alert("Error saving search");
        });
    });
  }

  // Functions are defined globally to work with onclick handlers
});

// Global function for managing saved searches
function showSavedSearches() {
  fetch("/scholar/api/saved-searches/", {
    headers: {
      "X-CSRFToken": getCookie("csrftoken"),
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "success") {
        displaySavedSearchesModal(data.searches);
      } else {
        alert("Error loading saved searches");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Error loading saved searches");
    });
}

function displaySavedSearchesModal(searches) {
  const modal = document.createElement("div");
  modal.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.5); z-index: 1000; display: flex;
        align-items: center; justify-content: center;
    `;

  const searchList = searches
    .map(
      (search) => `
        <div class="d-flex justify-content-between align-items-center p-2 border-bottom">
            <div>
                <strong>${search.name}</strong><br>
                <small class="text-muted">Query: ${search.query}</small><br>
                <small class="text-muted">Saved: ${new Date(search.created_at).toLocaleDateString()}</small>
            </div>
            <div>
                <button class="btn btn-sm btn-outline-primary me-2" onclick="loadSavedSearch('${search.id}')">
                    <i class="fas fa-search"></i> Load
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteSavedSearch('${search.id}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `,
    )
    .join("");

  modal.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 8px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto;">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h5>Saved Searches</h5>
                <button class="btn btn-close" onclick="this.closest('div[style*=\"position: fixed\"]').remove()"></button>
            </div>
            <div class="saved-searches-list">
                ${searches.length > 0 ? searchList : '<p class="text-muted text-center">No saved searches yet.</p>'}
            </div>
        </div>
    `;

  document.body.appendChild(modal);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.remove();
  });
}

function loadSavedSearch(searchId) {
  fetch(`/scholar/api/saved-searches/${searchId}/`, {
    headers: {
      "X-CSRFToken": getCookie("csrftoken"),
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "success") {
        const search = data.search;

        // Load query
        document.querySelector('input[name="q"]').value = search.query;

        // Load filters
        Object.entries(search.filters).forEach(([name, value]) => {
          const input = document.querySelector(`[name="${name}"]`);
          if (input) {
            if (input.type === "checkbox" || input.type === "radio") {
              if (input.value === value) {
                input.checked = true;
              }
            } else {
              input.value = value;
            }
          }
        });

        // Submit the form
        document.querySelector("form").submit();

        // Close modal
        document.querySelector('div[style*="position: fixed"]').remove();
      } else {
        alert("Error loading saved search");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Error loading saved search");
    });
}

function deleteSavedSearch(searchId) {
  if (!confirm("Are you sure you want to delete this saved search?")) return;

  fetch(`/scholar/api/saved-searches/${searchId}/`, {
    method: "DELETE",
    headers: {
      "X-CSRFToken": getCookie("csrftoken"),
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "success") {
        // Refresh the modal
        showSavedSearches();
      } else {
        alert("Error deleting saved search");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Error deleting saved search");
    });
}

// Global functions for file handling
function viewOnWeb(link, event) {
  // Check if this is a Ctrl+Click, Cmd+Click, middle-click, or right-click
  // In these cases, let the browser handle it normally (just open the href)
  if (
    event.ctrlKey ||
    event.metaKey ||
    event.button === 1 ||
    event.button === 2
  ) {
    return true; // Allow default behavior
  }

  // For normal left-click, open all URLs
  event.preventDefault();

  const resultCard = link.closest(".result-card");
  const paperTitle = resultCard.dataset.title;
  const doi = resultCard.dataset.doi;
  const pmid = resultCard.dataset.pmid;
  const arxivId = resultCard.dataset.arxivId;
  const externalUrl = resultCard.dataset.externalUrl;
  const source = resultCard.dataset.source;

  // Collect all available URLs
  const urls = [];

  // Add DOI URL if available
  if (doi && doi.trim()) {
    urls.push({ type: "DOI", url: `https://doi.org/${doi}` });
  }

  // Add PMID URL if available
  if (pmid && pmid.trim()) {
    urls.push({
      type: "PubMed",
      url: `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`,
    });
  }

  // Add arXiv URL if available
  if (arxivId && arxivId.trim()) {
    urls.push({ type: "arXiv", url: `https://arxiv.org/abs/${arxivId}` });
  }

  // Add external URL if available and not duplicate
  if (externalUrl && externalUrl.trim()) {
    // Check if it's not already a DOI URL
    if (!externalUrl.includes("doi.org")) {
      urls.push({ type: "External", url: externalUrl });
    }
  }

  // If no URLs found, fallback to Google Scholar search
  if (urls.length === 0) {
    urls.push({
      type: "Google Scholar",
      url: `https://scholar.google.com/scholar?q=${encodeURIComponent(paperTitle)}`,
    });
  }

  // Open all URLs in new tabs
  urls.forEach((item) => {
    window.open(item.url, "_blank");
  });

  return false; // Prevent default link behavior for normal clicks
}

function exportCitation(btn, format) {
  const resultCard = btn.closest(".result-card");
  const paperId = resultCard.dataset.paperId;

  if (!paperId) {
    alert("Error: Paper ID not found. Please try refreshing the page.");
    return;
  }

  // Show loading state
  const originalText = btn.innerHTML;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Exporting...';
  btn.disabled = true;

  // Export citation in requested format
  fetch(`/scholar/api/export/${format}/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: JSON.stringify({
      paper_ids: [paperId],
      collection_name: "single_export",
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        // Create download link
        const blob = new Blob([data.content], { type: "text/plain" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = data.filename;
        a.click();
        window.URL.revokeObjectURL(url);

        // Show success message
        showToast(
          `Citation exported successfully as ${format.toUpperCase()}!`,
          "success",
        );
      } else {
        alert(`Error exporting citation: ${data.error || "Unknown error"}`);
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Error exporting citation. Please try again.");
    })
    .finally(() => {
      // Reset button state
      btn.innerHTML = originalText;
      btn.disabled = false;
    });
}

function showBibTeX(btn) {
  const resultCard = btn.closest(".result-card");
  const paperTitle = resultCard.dataset.title;
  const authors = resultCard.dataset.authors;
  const year = resultCard.dataset.year;
  const journal = resultCard.dataset.journal;

  // Get citation from backend
  const params = new URLSearchParams({
    title: paperTitle,
    authors: authors,
    year: year,
    journal: journal,
  });

  fetch("/scholar/api/get-citation/?" + params)
    .then((response) => response.json())
    .then((data) => {
      const bibtex = data.bibtex;

      // Create a modal-like display for BibTeX
      const modal = document.createElement("div");
      modal.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); z-index: 1000; display: flex;
            align-items: center; justify-content: center;
        `;

      modal.innerHTML = `
            <div style="background: white; padding: 2rem; border-radius: 8px; max-width: 600px; width: 90%;">
                <h5>BibTeX Citation Preview</h5>
                <textarea readonly style="width: 100%; height: 200px; font-family: monospace; font-size: 12px; border: 1px solid #ddd; padding: 1rem;">${bibtex}</textarea>
                <div class="mt-3">
                    <button class="btn btn-primary me-2" onclick="navigator.clipboard.writeText(\`${bibtex.replace(/`/g, "\\`")}\`).then(() => alert('Copied to clipboard!'))">Copy to Clipboard</button>
                    <button class="btn btn-secondary" onclick="this.closest('div[style*=\\"position: fixed\\"]').remove()">Close</button>
                </div>
            </div>
        `;

      document.body.appendChild(modal);
      modal.addEventListener("click", (e) => {
        if (e.target === modal) modal.remove();
      });
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Error generating citation. Please try again.");
    });
}

function saveToLibrary(btn) {
  const resultCard = btn.closest(".result-card");
  const paperId = resultCard.dataset.paperId;
  const paperTitle = resultCard.dataset.title;

  // Try multiple ways to get selected project
  let selectedProject = "";

  // 1. Check sessionStorage from project selector
  const projectIdFromSession = sessionStorage.getItem(
    "scholar_selected_project_id",
  );
  if (projectIdFromSession) {
    selectedProject = projectIdFromSession;
  }

  // 2. Fall back to project select in BibTeX form (if exists)
  if (!selectedProject) {
    const projectSelect = document.querySelector('select[name="project"]');
    if (projectSelect) {
      selectedProject = projectSelect.value;
    }
  }

  // Send save request to backend
  fetch("/scholar/api/save-paper/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: JSON.stringify({
      paper_id: paperId,
      title: paperTitle,
      project: selectedProject,
    }),
  })
    .then((response) => {
      if (response.status === 401) {
        // Not authenticated
        return response.json().then((data) => {
          if (data.status === "signup_required") {
            // Show signup prompt
            const signupPrompt = confirm(
              data.message + "\n\nWould you like to sign up now?",
            );
            if (signupPrompt) {
              window.location.href = data.signup_url;
            }
          }
          throw new Error("Not authenticated");
        });
      }
      return response.json();
    })
    .then((data) => {
      if (data.status === "success") {
        // Visual feedback
        btn.innerHTML = "⭐ In Library";
        btn.classList.remove("btn-outline-warning");
        btn.classList.add("btn-warning");
        alert(data.message);
      } else if (data.status !== "signup_required") {
        alert(data.message || "Error saving paper");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      if (error.message !== "Not authenticated") {
        alert("Error saving paper. Please try again.");
      }
    });
}

function generateBibTeX(btn) {
  const resultCard = btn.closest(".result-card");
  const paperTitle = resultCard.dataset.title;
  const authors = resultCard.dataset.authors;
  const year = resultCard.dataset.year;
  const journal = resultCard.dataset.journal;

  // Get citation from backend
  const params = new URLSearchParams({
    title: paperTitle,
    authors: authors,
    year: year,
    journal: journal,
  });

  fetch("/scholar/api/get-citation/?" + params)
    .then((response) => response.json())
    .then((data) => {
      const bibtex = data.bibtex;

      // Copy to clipboard
      navigator.clipboard
        .writeText(bibtex)
        .then(() => {
          alert("BibTeX citation copied to clipboard!\n\n" + bibtex);
        })
        .catch(() => {
          // Fallback for older browsers
          const textArea = document.createElement("textarea");
          textArea.value = bibtex;
          document.body.appendChild(textArea);
          textArea.select();
          document.execCommand("copy");
          document.body.removeChild(textArea);
          alert("BibTeX citation copied to clipboard!\n\n" + bibtex);
        });
    })
    .catch((error) => {
      console.error("Error:", error);
      alert("Error generating citation. Please try again.");
    });
}

function uploadMyFiles(btn) {
  const resultCard = btn.closest(".result-card");
  const paperId = resultCard.dataset.paperId;
  const paperTitle = resultCard.dataset.title;

  // Create file input dialog
  const fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.multiple = true;
  fileInput.accept = ".pdf,.bib,.bibtex";

  fileInput.onchange = function (e) {
    const files = Array.from(e.target.files);

    if (files.length === 0) return;

    // Upload each file
    const uploadPromises = files.map((file) => {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("paper_id", paperId);
      formData.append(
        "file_type",
        file.name.toLowerCase().endsWith(".pdf") ? "pdf" : "bibtex",
      );

      return fetch("/scholar/api/upload-file/", {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: formData,
      }).then((response) => response.json());
    });

    Promise.all(uploadPromises)
      .then((results) => {
        const successCount = results.filter(
          (r) => r.status === "success",
        ).length;
        if (successCount > 0) {
          // Visual feedback
          btn.innerHTML = "✓ Uploaded";
          btn.classList.remove("btn-outline-success");
          btn.classList.add("btn-success");
          alert(
            `Successfully uploaded ${successCount} file(s) for: ${paperTitle}`,
          );
        } else {
          alert("Error uploading files. Please try again.");
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("Error uploading files. Please try again.");
      });
  };

  fileInput.click();
}

// Bulk export functions
function selectAllPapers() {
  const checkboxes = document.querySelectorAll(".paper-checkbox");
  const allChecked = Array.from(checkboxes).every((cb) => cb.checked);

  checkboxes.forEach((checkbox) => {
    checkbox.checked = !allChecked;
  });

  // Bulk actions removed
}

function bulkExportCitations(format) {
  const selectedCheckboxes = document.querySelectorAll(
    ".paper-select-checkbox:checked",
  );

  if (selectedCheckboxes.length === 0) {
    alert("Please select at least one paper to export.");
    return;
  }

  const paperIds = Array.from(selectedCheckboxes).map(
    (cb) => cb.dataset.paperId,
  );

  // Show loading state
  showToast(
    `Exporting ${selectedCheckboxes.length} citations as ${format.toUpperCase()}...`,
    "info",
  );

  // Export citations in requested format
  fetch(`/scholar/api/export/${format}/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: JSON.stringify({
      paper_ids: paperIds,
      collection_name: "bulk_search_export",
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        // Create download link
        const blob = new Blob([data.content], { type: "text/plain" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = data.filename;
        a.click();
        window.URL.revokeObjectURL(url);

        // Show success message
        showToast(
          `Successfully exported ${data.count} citations as ${format.toUpperCase()}!`,
          "success",
        );

        // Clear selections and update button state
        document
          .querySelectorAll(".paper-select-checkbox:checked")
          .forEach((cb) => (cb.checked = false));
        // Trigger change event to update button state
        const changeEvent = new Event("change", { bubbles: true });
        document
          .querySelectorAll(".paper-select-checkbox")
          .forEach((cb) => cb.dispatchEvent(changeEvent));
      } else {
        showToast(
          `Error exporting citations: ${data.error || "Unknown error"}`,
          "danger",
        );
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      showToast("Error exporting citations. Please try again.", "danger");
    });
}

// Helper function to show toast notifications
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
  toast.style.cssText =
    "top: 20px; right: 20px; z-index: 1050; min-width: 300px;";
  toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

  document.body.appendChild(toast);

  // Auto-remove after 3 seconds
  setTimeout(() => {
    if (toast.parentNode) {
      toast.remove();
    }
  }, 3000);
}

// Helper function to get CSRF token
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// BibTeX Job Status Polling
function pollBibtexJobStatus(jobId, attempts = 0) {
  // Store job ID globally for "Open All URLs" button
  window.currentBibtexJobId = jobId;

  if (attempts > 180) {
    console.error("[Scholar Index] Polling timeout after 180 attempts");
    document.getElementById("processingLog").textContent +=
      "\n\n✗ Polling timeout. Please refresh the page.";
    return;
  }

  fetch(`/scholar/api/bibtex/job/${jobId}/status/`)
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then((data) => {
      // Update progress
      if (data.progress_percentage !== undefined) {
        document.getElementById("progressBar").style.width =
          `${data.progress_percentage}%`;
        document.getElementById("progressPercentage").textContent =
          `${data.progress_percentage}%`;
      }

      // Update paper counts
      if (data.total_papers !== undefined) {
        let text = `${data.processed_papers} / ${data.total_papers} papers processed`;
        if (data.failed_papers > 0) text += ` (${data.failed_papers} failed)`;
        document.getElementById("progressDetails").textContent = text;
      }

      // Update log
      if (data.log) {
        document.getElementById("processingLog").textContent = data.log;
        document.getElementById("processingLog").scrollTop =
          document.getElementById("processingLog").scrollHeight;
      }

      // Check if done
      if (data.status === "completed") {
        console.log("[Scholar Index] Job completed! Setting up download...");
        const downloadUrl = `/scholar/api/bibtex/job/${jobId}/download/`;
        const urlsUrl = `/scholar/api/bibtex/job/${jobId}/urls/`;
        console.log("[Scholar Index] Download URL:", downloadUrl);

        // Enable download button and set URL
        const downloadBtn = document.getElementById("downloadBtn");
        downloadBtn.href = downloadUrl;
        downloadBtn.classList.remove("disabled");
        downloadBtn.style.opacity = "1";

        // Enable all buttons now that job is complete
        const showDiffBtn = document.getElementById("showDiffBtn");
        const openUrlsBtn = document.getElementById("openUrlsBtn");

        if (showDiffBtn) {
          showDiffBtn.disabled = false;
          showDiffBtn.style.opacity = "1";
          console.log("[Scholar Index] ✓ Show Diff button enabled");
        } else {
          console.error("[Scholar Index] ✗ Show Diff button not found!");
        }

        if (openUrlsBtn) {
          openUrlsBtn.disabled = false;
          openUrlsBtn.style.opacity = "1";
          openUrlsBtn.style.cursor = "pointer";
          console.log("[Scholar Index] ✓ Open URLs button enabled");
        } else {
          console.error("[Scholar Index] ✗ Open URLs button not found!");
        }

        console.log("[Scholar Index] All buttons enabled");

        // Fetch URL count for the "Open All URLs" button
        fetch(urlsUrl)
          .then((response) => response.json())
          .then((urlData) => {
            const count = urlData.total_urls || 0;
            document.getElementById("urlCount").textContent = count;
            console.log("[Scholar Index] URL count updated:", count);
          })
          .catch((error) => {
            console.error("[Scholar Index] Failed to fetch URL count:", error);
            document.getElementById("urlCount").textContent = "?";
          });

        // Auto-download the enriched file
        console.log(
          "[Scholar Index] Triggering auto-download for:",
          downloadUrl,
        );
        console.log(
          "[Scholar Index] autoDownloadBibtexFile function exists?",
          typeof autoDownloadBibtexFile,
        );
        try {
          autoDownloadBibtexFile(downloadUrl);
        } catch (error) {
          console.error("[Scholar Index] Auto-download failed:", error);
          // Fallback: let user click the button
          document.getElementById("processingLog").textContent +=
            "\n\n✓ Download ready! Click the button below to download.";
        }
      } else if (data.status === "failed") {
        console.log("[Scholar Index] Job failed:", data.error_message);
        document.getElementById("processingLog").textContent +=
          "\n\n✗ ERROR: " + (data.error_message || "Unknown error");
        setTimeout(() => resetBibtexForm(), 5000);
      } else {
        setTimeout(() => pollBibtexJobStatus(jobId, attempts + 1), 2000);
      }
    })
    .catch((error) => {
      console.error("Polling error:", error);
      setTimeout(() => pollBibtexJobStatus(jobId, attempts + 1), 5000);
    });
}

// Copy BibTeX processing log to clipboard
document.addEventListener("DOMContentLoaded", function () {
  const copyBibtexLogBtn = document.getElementById("copyBibtexLogBtn");
  const processingLog = document.getElementById("processingLog");

  if (copyBibtexLogBtn && processingLog) {
    copyBibtexLogBtn.addEventListener("click", async function () {
      try {
        const logText = processingLog.textContent;
        await navigator.clipboard.writeText(logText);

        // Visual feedback
        const originalHTML = this.innerHTML;
        this.innerHTML = '<i class="fas fa-check"></i> Copied!';
        this.style.background = "var(--success-color)";
        this.style.color = "var(--white)";

        setTimeout(() => {
          this.innerHTML = originalHTML;
          this.style.background = "var(--color-btn-bg)";
          this.style.color = "var(--color-fg-default)";
        }, 2000);
      } catch (err) {
        console.error("Failed to copy log:", err);

        // Fallback: select text for manual copy
        const range = document.createRange();
        range.selectNodeContents(processingLog);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);

        // Show error feedback
        this.innerHTML =
          '<i class="fas fa-exclamation-triangle"></i> Select text manually';
        this.style.background = "var(--error-color)";
        this.style.color = "var(--white)";

        setTimeout(() => {
          this.innerHTML = '<i class="fas fa-copy"></i> Copy Log';
          this.style.background = "var(--color-btn-bg)";
          this.style.color = "var(--color-fg-default)";
        }, 3000);
      }
    });
  }
});

// Resource Monitoring - Poll for resource status
// Note: resourceMonitorInterval is now managed by queue-management.js
// let resourceMonitorInterval = null; // REMOVED - duplicate declaration

function updateResourceMonitor() {
  fetch(window.SCHOLAR_CONFIG.urls.resourceStatus)
    .then((response) => response.json())
    .then((data) => {
      // Update system stats (only Active Jobs and Queued - CPU/Memory removed from UI)
      const activeJobsEl = document.getElementById("activeJobsCount");
      const queuedJobsEl = document.getElementById("queuedJobsCount");

      if (activeJobsEl) activeJobsEl.textContent = data.jobs.active_count;
      if (queuedJobsEl) queuedJobsEl.textContent = data.jobs.queued_count;

      // Update refresh time
      const updateTime = new Date(data.timestamp);
      document.getElementById("resourceRefreshTime").textContent =
        `Updated ${updateTime.toLocaleTimeString()}`;

      // Show/hide active jobs list
      const activeJobsList = document.getElementById("activeJobsList");
      const activeJobsContent = document.getElementById("activeJobsContent");

      // Show active list if user has active jobs OR if there are system active jobs
      if (data.jobs.active.length > 0) {
        activeJobsList.style.display = "block";
        activeJobsContent.innerHTML = data.jobs.active
          .map(
            (job) => `
                    <div style="background: var(--color-canvas-default); padding: 0.75rem; border-radius: 6px; margin-bottom: 0.5rem; border-left: 3px solid var(--scitex-color-03); animation: pulse 2s infinite;">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.25rem;">
                            <div style="color: var(--color-fg-default); font-weight: 600; font-size: 0.9rem;">
                                <i class="fas fa-cog fa-spin"></i> ${job.filename}
                            </div>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                ${
                                  job.can_cancel
                                    ? `
                                    <button onclick="cancelJob('${job.id}')" style="background: var(--error-color); color: var(--white); border: none; border-radius: 4px; padding: 0.25rem 0.5rem; cursor: pointer; font-size: 0.75rem;" title="Cancel job">
                                        <i class="fas fa-times"></i>
                                    </button>
                                `
                                    : ""
                                }
                            </div>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="flex: 1; margin-right: 1rem;">
                                <div style="background: var(--color-border-default); border-radius: 4px; height: 6px; overflow: hidden;">
                                    <div style="background: var(--scitex-color-03); height: 100%; width: ${job.progress}%; transition: width 0.3s;"></div>
                                </div>
                            </div>
                            <div style="color: var(--color-fg-muted); font-size: 0.85rem; white-space: nowrap;">
                                ${job.progress}% (${job.processed}/${job.total})
                            </div>
                        </div>
                    </div>
                `,
          )
          .join("");
      } else if (data.jobs.active_count > 0) {
        // System has active jobs, but none belong to this user
        activeJobsList.style.display = "block";
        activeJobsContent.innerHTML = `
                    <div style="background: var(--color-canvas-subtle); padding: 1rem; border-radius: 6px; text-align: center; color: var(--color-fg-muted);">
                        <i class="fas fa-info-circle"></i> ${data.jobs.active_count} job(s) currently processing
                        <div style="font-size: 0.85rem; margin-top: 0.25rem;">
                            (Other users' jobs - hidden for privacy)
                        </div>
                    </div>
                `;
      } else {
        activeJobsList.style.display = "none";
      }

      // Show/hide queued jobs list
      const queuedJobsList = document.getElementById("queuedJobsList");
      const queuedJobsContent = document.getElementById("queuedJobsContent");

      // Show queued list if user has queued jobs OR if there are system queues
      if (data.jobs.queued.length > 0) {
        queuedJobsList.style.display = "block";
        queuedJobsContent.innerHTML = data.jobs.queued
          .map((job) => {
            // Visual indicator based on queue position
            const positionColor =
              job.position === 1
                ? "var(--success-color)"
                : job.position === 2
                  ? "var(--scitex-color-03)"
                  : "var(--warning-color)";
            const positionBadge =
              job.position === 1
                ? '<i class="fas fa-star"></i> Next up'
                : job.position === 2
                  ? '<i class="fas fa-arrow-up"></i> 2nd in line'
                  : `<i class="fas fa-hourglass-half"></i> Position #${job.position}`;

            return `
                        <div style="background: var(--color-canvas-default); padding: 0.75rem; border-radius: 6px; margin-bottom: 0.5rem; border-left: 3px solid ${positionColor};">
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div style="flex: 1;">
                                    <div style="color: var(--color-fg-default); font-weight: 600; font-size: 0.9rem; margin-bottom: 0.25rem;">
                                        <i class="fas fa-file-code"></i> ${job.filename}
                                    </div>
                                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                                        <span style="color: ${positionColor}; font-size: 0.85rem; font-weight: 600;">
                                            ${positionBadge}
                                        </span>
                                        ${
                                          job.position > 3
                                            ? `
                                            <span style="color: var(--color-fg-muted); font-size: 0.75rem;">
                                                (${job.position - 1} jobs ahead)
                                            </span>
                                        `
                                            : ""
                                        }
                                    </div>
                                </div>
                                <div style="display: flex; align-items: center; gap: 0.5rem;">
                                    ${
                                      job.can_cancel
                                        ? `
                                        <button onclick="cancelJob('${job.id}')" style="background: var(--error-color); color: var(--white); border: none; border-radius: 4px; padding: 0.25rem 0.5rem; cursor: pointer; font-size: 0.75rem;" title="Cancel job">
                                            <i class="fas fa-times"></i>
                                        </button>
                                    `
                                        : ""
                                    }
                                </div>
                            </div>
                        </div>
                    `;
          })
          .join("");
      } else if (data.jobs.queued_count > 0) {
        // System has queued jobs, but none belong to this user
        queuedJobsList.style.display = "block";
        queuedJobsContent.innerHTML = `
                    <div style="background: var(--color-canvas-subtle); padding: 1rem; border-radius: 6px; text-align: center; color: var(--color-fg-muted);">
                        <i class="fas fa-info-circle"></i> ${data.jobs.queued_count} job(s) in system queue
                        <div style="font-size: 0.85rem; margin-top: 0.25rem;">
                            (Other users' jobs - hidden for privacy)
                        </div>
                    </div>
                `;
      } else {
        queuedJobsList.style.display = "none";
      }
    })
    .catch((error) => {
      console.error("Failed to fetch resource status:", error);
      document.getElementById("resourceRefreshTime").textContent =
        "Error fetching data";
    });
}

// Cancel a job
function cancelJob(jobId) {
  if (!confirm("Are you sure you want to cancel this job?")) {
    return;
  }

  // Get CSRF token
  const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

  fetch(`/scholar/api/bibtex/job/${jobId}/cancel/`, {
    method: "POST",
    headers: {
      "X-Requested-With": "XMLHttpRequest",
      "X-CSRFToken": csrfToken,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        alert("Job cancelled successfully");
        // Refresh resource monitor
        updateResourceMonitor();
      } else {
        alert("Failed to cancel job: " + (data.error || "Unknown error"));
      }
    })
    .catch((error) => {
      console.error("Error cancelling job:", error);
      alert("Failed to cancel job");
    });
}

// Start resource monitoring on page load
document.addEventListener("DOMContentLoaded", function () {
  // Initial update
  updateResourceMonitor();

  // Poll every 3 seconds
  resourceMonitorInterval = setInterval(updateResourceMonitor, 3000);
});

// Clean up interval when leaving page
window.addEventListener("beforeunload", function () {
  if (resourceMonitorInterval) {
    clearInterval(resourceMonitorInterval);
  }
});

// Auto-download BibTeX file when enrichment completes
function autoDownloadBibtexFile(url) {
  console.log("[Auto-Download] Starting download for:", url);

  fetch(url)
    .then((response) => {
      console.log("[Auto-Download] Response status:", response.status);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      // Extract filename from headers
      let filename = "enriched_bibliography.bib";
      const contentDisposition = response.headers.get("Content-Disposition");
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?(.+?)"?$/);
        if (match) filename = match[1];
      }
      console.log("[Auto-Download] Filename:", filename);

      return response.blob().then((blob) => ({ blob, filename }));
    })
    .then(({ blob, filename }) => {
      console.log("[Auto-Download] Creating download link...");
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename;
      a.style.display = "none";
      document.body.appendChild(a);
      a.click();

      setTimeout(() => {
        document.body.removeChild(a);
        window.URL.revokeObjectURL(blobUrl);
        console.log("[Auto-Download] ✓ Download completed");
      }, 100);
    })
    .catch((error) => {
      console.error("[Auto-Download] ✗ Failed:", error);
      console.log("[Auto-Download] Trying fallback method...");

      // Fallback: direct link
      const a = document.createElement("a");
      a.href = url;
      a.download = "enriched_bibliography.bib";
      document.body.appendChild(a);
      a.click();
      setTimeout(() => document.body.removeChild(a), 100);
    });
}

// Open all paper URLs from enriched BibTeX file
function openAllPaperUrls() {
  const jobId = window.currentBibtexJobId;
  if (!jobId) {
    alert("No job ID available. Please wait for enrichment to complete.");
    return;
  }

  console.log("[Open URLs] Fetching URLs for job:", jobId);
  const urlsEndpoint = `/scholar/api/bibtex/job/${jobId}/urls/`;

  fetch(urlsEndpoint)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      console.log("[Open URLs] Received data:", data);

      if (data.urls && data.urls.length > 0) {
        const confirmMsg =
          `Open ${data.total_urls} paper URL(s) in new tabs?\n\n` +
          `Note: Your browser may block some pop-ups. Please allow pop-ups for this site if needed.`;

        if (confirm(confirmMsg)) {
          console.log(`[Open URLs] Opening ${data.urls.length} URLs...`);

          // Open all URLs immediately (no setTimeout to avoid popup blocker)
          let openedCount = 0;
          data.urls.forEach((paper, index) => {
            console.log(
              `[Open URLs] Opening: ${paper.title.substring(0, 50)}... (${paper.type})`,
            );
            const newWindow = window.open(paper.url, "_blank");
            if (newWindow) {
              openedCount++;
            }
          });

          // Only show message if some tabs were blocked
          if (openedCount < data.urls.length) {
            alert(
              `⚠️ Opened ${openedCount} out of ${data.urls.length} URLs.\n\nSome tabs were blocked by your browser's popup blocker.\nPlease allow popups for this site and try again.`,
            );
          }
          // Success case: no message, tabs just open silently
        }
      } else {
        alert(
          "No URLs found in the enriched BibTeX file.\n\nThis could mean:\n- Papers don't have DOI or URL fields\n- Enrichment didn't add URLs\n- Try downloading the file to check",
        );
      }
    })
    .catch((error) => {
      console.error("[Open URLs] Error:", error);
      alert(
        `Failed to fetch URLs: ${error.message}\n\nPlease try downloading the BibTeX file manually.`,
      );
    });
}

// Show BibTeX diff - what was enhanced
function showBibtexDiff() {
  const jobId = window.currentBibtexJobId;
  if (!jobId) {
    alert("No job ID available. Please wait for enrichment to complete.");
    return;
  }

  // Show modal
  document.getElementById("bibtexDiffModal").style.display = "block";
  document.getElementById("bibtexDiffContent").innerHTML =
    "Loading comparison...";

  // Fetch diff data
  fetch(`/scholar/api/bibtex/job/${jobId}/diff/`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.success) {
        displayBibtexDiff(data.diff, data.stats);
      } else {
        document.getElementById("bibtexDiffContent").innerHTML =
          `<div style="color: var(--error-color);">Error: ${data.error || "Failed to generate diff"}</div>`;
      }
    })
    .catch((error) => {
      console.error("Error fetching diff:", error);
      document.getElementById("bibtexDiffContent").innerHTML =
        `<div style="color: var(--error-color);">Failed to load comparison: ${error.message}</div>`;
    });
}

// Display the diff in a readable format (GitHub-style)
function displayBibtexDiff(diffData, stats) {
  let html = "";

  // Show statistics at the top
  if (stats) {
    html += `<div style="background: #f6f8fa; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem; border-left: 4px solid #28a745;">`;
    html += `<h3 style="color: #24292e; margin-bottom: 1rem; font-size: 1.2rem;">
            <i class="fas fa-chart-bar"></i> Enhancement Statistics
        </h3>`;
    html += `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">`;
    html += `<div style="text-align: center;">
            <div style="color: #586069; font-size: 0.85rem;">Total Entries</div>
            <div style="color: #0366d6; font-size: 1.8rem; font-weight: 700;">${stats.total_entries}</div>
        </div>`;
    html += `<div style="text-align: center;">
            <div style="color: #586069; font-size: 0.85rem;">Entries Enhanced</div>
            <div style="color: #28a745; font-size: 1.8rem; font-weight: 700;">${stats.entries_enhanced}</div>
        </div>`;
    html += `<div style="text-align: center;">
            <div style="color: #586069; font-size: 0.85rem;">Fields Added</div>
            <div style="color: #28a745; font-size: 1.8rem; font-weight: 700;">${stats.total_fields_added}</div>
        </div>`;
    html += `<div style="text-align: center;">
            <div style="color: #586069; font-size: 0.85rem;">Enhancement Rate</div>
            <div style="color: #0366d6; font-size: 1.8rem; font-weight: 700;">${stats.enhancement_rate}%</div>
        </div>`;
    html += `</div></div>`;
  }

  if (!diffData || diffData.length === 0) {
    html +=
      '<div style="text-align: center; padding: 3rem; color: #586069; background: #ffffff;">';
    html +=
      '<i class="fas fa-check-circle" style="font-size: 3rem; margin-bottom: 1rem; display: block; color: #28a745;"></i>';
    html +=
      '<p style="font-size: 1.1rem;">All entries are already complete!</p>';
    html +=
      '<p style="font-size: 0.9rem;">No new fields were added during enrichment.</p>';
    html += "</div>";
    document.getElementById("bibtexDiffContent").innerHTML = html;
    return;
  }

  // Display ALL entries in GitHub-style diff format
  diffData.forEach((entry) => {
    const hasChanges = entry.has_changes || false;

    html += `<div style="margin-bottom: 1.5rem; border: 1px solid #d1d5da; border-radius: 6px; overflow: hidden; background: #ffffff;">`;

    // Entry header
    html += `<div style="background: #f6f8fa; padding: 0.5rem 1rem; border-bottom: 1px solid #d1d5da; font-family: monospace; font-size: 0.9rem; color: #24292e; font-weight: 600;">`;
    html += `@${entry.type}{${entry.key}}`;
    if (hasChanges) {
      html += ` <span style="color: #28a745; font-size: 0.85rem;"><i class="fas fa-check-circle"></i></span>`;
    }
    html += `</div>`;

    // Diff content
    html += `<div style="font-family: 'Consolas', 'Monaco', 'Courier New', monospace; font-size: 0.85rem; line-height: 1.5;">`;

    // Opening brace
    html += `<div style="background: #ffffff; padding: 0.25rem 1rem; color: #24292e;">{</div>`;

    // Original fields (black)
    if (
      entry.original_fields &&
      Object.keys(entry.original_fields).length > 0
    ) {
      for (const [key, value] of Object.entries(entry.original_fields)) {
        html += `<div style="background: #ffffff; padding: 0.25rem 1rem; color: #24292e; word-wrap: break-word; white-space: pre-wrap;">`;
        html += `  ${key} = {${escapeHtml(value)}}`;
        html += `</div>`;
      }
    }

    // Added fields (green with + prefix)
    if (entry.added_fields && Object.keys(entry.added_fields).length > 0) {
      for (const [key, value] of Object.entries(entry.added_fields)) {
        html += `<div style="background: #e6ffed; padding: 0.25rem 1rem; color: #22863a; word-wrap: break-word; white-space: pre-wrap;">`;
        html += `+ ${key} = {${escapeHtml(value)}}`;
        html += `</div>`;
      }
    }

    // Closing brace
    html += `<div style="background: #ffffff; padding: 0.25rem 1rem; color: #24292e;">}</div>`;

    html += `</div></div>`;
  });

  document.getElementById("bibtexDiffContent").innerHTML = html;
}

// Helper function to escape HTML
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Close BibTeX diff modal
function closeBibtexDiff() {
  document.getElementById("bibtexDiffModal").style.display = "none";
}

// Format Citation Counts with Comma Separators
function formatCitationCounts() {
  const citationElements = document.querySelectorAll(".citation-count");
  citationElements.forEach((element) => {
    const count = parseInt(element.textContent);
    if (!isNaN(count)) {
      element.textContent = count.toLocaleString("en-US");
    }
  });
}

// Call formatting on page load
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", formatCitationCounts);
} else {
  formatCitationCounts();
}

// Also format when results are dynamically added (for AJAX results)
const formatCitationsObserver = new MutationObserver(function (mutations) {
  formatCitationCounts();
});

// Observe the results container for changes
const resultsContainer = document.getElementById("scitex-results-container");
if (resultsContainer) {
  formatCitationsObserver.observe(resultsContainer, {
    childList: true,
    subtree: true,
  });
}

// Global Abstract Toggle Management
document.addEventListener("DOMContentLoaded", function () {
  // Load saved abstract mode from localStorage
  const savedMode = localStorage.getItem("global_abstract_mode") || "truncated";

  // Set initial button state
  const toggleButtons = document.querySelectorAll(".global-abstract-toggle");
  toggleButtons.forEach((btn) => {
    if (btn.dataset.mode === savedMode) {
      btn.classList.remove("btn-outline-secondary");
      btn.classList.add("btn-primary");
    }
  });

  // Apply saved mode to all existing abstracts
  applyGlobalAbstractMode(savedMode);

  // Add click handlers to toggle buttons
  toggleButtons.forEach((btn) => {
    btn.addEventListener("click", function () {
      const mode = this.dataset.mode;

      // Update button states
      toggleButtons.forEach((b) => {
        b.classList.remove("btn-primary");
        b.classList.add("btn-outline-secondary");
      });
      this.classList.remove("btn-outline-secondary");
      this.classList.add("btn-primary");

      // Save mode and apply it
      localStorage.setItem("global_abstract_mode", mode);
      applyGlobalAbstractMode(mode);
    });
  });

  // Function to apply global abstract mode to all papers
  function applyGlobalAbstractMode(mode) {
    const abstracts = document.querySelectorAll(".abstract-preview");
    abstracts.forEach((abstract) => {
      abstract.classList.remove("mode-all", "mode-truncated", "mode-none");
      abstract.classList.add("mode-" + mode);
    });
  }
});

// Paper Selection Management for Bulk Export
document.addEventListener("DOMContentLoaded", function () {
  // Paper selection functionality
  const selectAllBtn = document.getElementById("selectAllResults");
  const deselectAllBtn = document.getElementById("deselectAllResults");
  const exportBtn = document.getElementById("exportSelectedBibtex");
  const selectedCountEl = document.getElementById("selectedCount");

  if (selectAllBtn && deselectAllBtn && exportBtn) {
    // Select All handler
    selectAllBtn.addEventListener("click", function () {
      const checkboxes = document.querySelectorAll(".paper-select-checkbox");
      checkboxes.forEach((checkbox) => {
        checkbox.checked = true;
      });
      updateExportButton();
    });

    // Deselect All handler
    deselectAllBtn.addEventListener("click", function () {
      const checkboxes = document.querySelectorAll(".paper-select-checkbox");
      checkboxes.forEach((checkbox) => {
        checkbox.checked = false;
      });
      updateExportButton();
    });

    // Individual checkbox change handler
    document.addEventListener("change", function (e) {
      if (e.target.classList.contains("paper-select-checkbox")) {
        updateExportButton();
      }
    });

    // Export button click handler
    exportBtn.addEventListener("click", function () {
      const selectedCheckboxes = document.querySelectorAll(
        ".paper-select-checkbox:checked",
      );
      if (selectedCheckboxes.length === 0) {
        alert("Please select at least one paper to export.");
        return;
      }

      // No need to validate search query - just export selected papers
      bulkExportCitations("bibtex");
    });

    // Function to update export button state
    function updateExportButton() {
      const checkboxes = document.querySelectorAll(".paper-select-checkbox");
      const selectedCount = document.querySelectorAll(
        ".paper-select-checkbox:checked",
      ).length;
      const totalCount = checkboxes.length;

      // Update selected count display
      if (selectedCountEl) {
        selectedCountEl.textContent = `${selectedCount} of ${totalCount} selected`;
      }

      // Enable/disable export button
      if (exportBtn) {
        if (selectedCount > 0) {
          exportBtn.disabled = false;
          exportBtn.classList.remove("disabled");
          exportBtn.style.opacity = "1";
          exportBtn.style.cursor = "pointer";
        } else {
          exportBtn.disabled = true;
          exportBtn.classList.add("disabled");
          exportBtn.style.opacity = "0.5";
          exportBtn.style.cursor = "not-allowed";
        }
      }
    }

    // Initialize button state on page load
    updateExportButton();
  }
});
