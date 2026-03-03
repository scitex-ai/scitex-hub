// Toggle sidebar sections (expand/collapse)
function toggleSidebarSection(sectionId) {
  const submenu = document.getElementById("submenu-" + sectionId);
  const button = event.currentTarget;
  const icon = button.querySelector(".sidebar-toggle-icon");

  if (submenu.style.display === "none" || submenu.style.display === "") {
    submenu.style.display = "block";
    icon.style.transform = "rotate(180deg)";
  } else {
    submenu.style.display = "none";
    icon.style.transform = "rotate(0deg)";
  }
}

// Auto-expand section when navigating to a component within it
document.addEventListener("DOMContentLoaded", function () {
  // If there's a hash in the URL, expand the relevant section
  if (window.location.hash) {
    const hash = window.location.hash.substring(1);

    // Check if it's a component link
    if (hash.startsWith("component-")) {
      // Find which category this component belongs to
      document.querySelectorAll(".sidebar-nav-submenu").forEach((submenu) => {
        const links = submenu.querySelectorAll("a");
        links.forEach((link) => {
          if (link.getAttribute("href") === "#" + hash) {
            submenu.style.display = "block";
            const button = submenu.previousElementSibling;
            if (button) {
              const icon = button.querySelector(".sidebar-toggle-icon");
              if (icon) icon.style.transform = "rotate(180deg)";
            }
          }
        });
      });
    }
  }
});

// Sidebar active state on scroll
document.addEventListener("DOMContentLoaded", function () {
  const sections = document.querySelectorAll(
    '[id^="category-"], [id^="component-"], #programmatic-components, #colors, #typography, #spacing, #theme, #components',
  );
  const navLinks = document.querySelectorAll(".sidebar-nav-item");

  function updateActiveLink() {
    let current = "";
    sections.forEach((section) => {
      const sectionTop = section.offsetTop;
      const sectionHeight = section.clientHeight;
      if (window.pageYOffset >= sectionTop - 150) {
        current = section.getAttribute("id");
      }
    });

    navLinks.forEach((link) => {
      link.classList.remove("sidebar-nav-item-active", "active");
      const href = link.getAttribute("href");
      if (href && href.substring(1) === current) {
        link.classList.add("sidebar-nav-item-active", "active");
      }
    });
  }

  window.addEventListener("scroll", updateActiveLink);
  updateActiveLink(); // Call on load
});

// Section filtering for design system
function showSection(sectionId) {
  // Hide all sections
  document.querySelectorAll(".design-section").forEach((section) => {
    section.style.display = "none";
  });

  // Show selected section
  const targetSection = document.getElementById(sectionId);
  if (targetSection) {
    targetSection.style.display = "block";
    // Scroll with offset to account for sticky header
    const headerOffset = 80; // Adjust based on your header height
    const elementPosition = targetSection.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

    window.scrollTo({
      top: offsetPosition,
      behavior: "smooth",
    });
  }

  // Update button states
  document.querySelectorAll(".section-btn").forEach((btn) => {
    btn.classList.remove("btn-primary", "btn-success");
    btn.classList.add("btn-outline-primary");
  });
  event.target.classList.remove("btn-outline-primary");
  event.target.classList.add("btn-success");

  // Update show all button
  document.getElementById("show-all-btn").textContent = "Show All";
}

function showAllSections() {
  // Show all sections
  document.querySelectorAll(".design-section").forEach((section) => {
    section.style.display = "block";
  });

  // Reset button states
  document.querySelectorAll(".section-btn").forEach((btn) => {
    btn.classList.remove("btn-success");
    btn.classList.add("btn-outline-primary");
  });

  // Update show all button
  document.getElementById("show-all-btn").textContent = "✓ Showing All";

  // Scroll to top
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// On page load, show all sections (don't hide any by default)
document.addEventListener("DOMContentLoaded", function () {
  // Ensure we're at the top of the page on initial load
  if (!window.location.hash) {
    window.scrollTo(0, 0);
  }

  // All sections are visible by default
  // Don't call showSection() on initial load to prevent unwanted scrolling
});
