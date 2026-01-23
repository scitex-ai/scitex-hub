/**
 * Remote credentials page functionality
 */

function toggleAddForm(): void {
  const form = document.getElementById('addCredentialForm');
  if (form) {
    form.classList.toggle('show');
  }
}

// Export for inline onclick handlers
(window as any).toggleAddForm = toggleAddForm;
