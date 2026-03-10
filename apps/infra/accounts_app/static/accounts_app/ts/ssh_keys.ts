/**
 * SSH Keys Management TypeScript
 * Handles SSH key upload, display, and deletion
 */

  // Tab switching for key types
  function showKeyTypeTab(tabName) {
      // Hide all tabs
      document.getElementById('workspace-tab-content').style.display = 'none';
      document.getElementById('git-tab-content').style.display = 'none';
      document.getElementById('gpg-tab-content').style.display = 'none';
      document.getElementById('remote-tab-content').style.display = 'none';

      // Show selected tab
      if (tabName === 'workspace') {
          document.getElementById('workspace-tab-content').style.display = 'block';
      } else if (tabName === 'git') {
          document.getElementById('git-tab-content').style.display = 'block';
      } else if (tabName === 'gpg') {
          document.getElementById('gpg-tab-content').style.display = 'block';
      } else if (tabName === 'remote') {
          document.getElementById('remote-tab-content').style.display = 'block';
      }

      // Update tab button styles
      const tabs = document.querySelectorAll('.key-type-tab');
      tabs.forEach(tab => {
          const isActive = tab.dataset.tab === tabName;
          tab.classList.toggle('active', isActive);

          if (isActive) {
              // Active tab styling
              tab.style.fontWeight = '600';
              tab.style.color = 'var(--color-fg-default)';

              // Different colors for different tabs
              if (tabName === 'workspace') {
                  tab.style.borderBottomColor = '#28a745';
              } else if (tabName === 'git') {
                  tab.style.borderBottomColor = 'var(--scitex-color-04)';
              } else if (tabName === 'remote') {
                  tab.style.borderBottomColor = '#ff6b35';  // Orange color for remote
              } else {
                  tab.style.borderBottomColor = 'var(--scitex-color-04)';
              }
          } else {
              // Inactive tab styling
              tab.style.borderBottomColor = 'transparent';
              tab.style.color = 'var(--color-fg-muted)';
              tab.style.fontWeight = '400';
          }
      });
  }

  // Toggle remote credential form
  function toggleRemoteForm() {
      const form = document.getElementById('add-remote-form');
      if (form.style.display === 'none' || form.style.display === '') {
          form.style.display = 'block';
      } else {
          form.style.display = 'none';
      }
  }
  function copySSHKey(event) {
      event.preventDefault();
      const keyElement = document.getElementById('ssh-public-key');
      const keyText = keyElement.textContent;

      navigator.clipboard.writeText(keyText).then(() => {
          const btn = event.target;
          const originalText = btn.innerHTML;
          btn.innerHTML = '✓ Copied!';
          setTimeout(() => {
              btn.innerHTML = originalText;
          }, 2000);
      }).catch(err => {
          alert('Failed to copy: ' + err);
      });
  }

  // Handle URL hash for deep linking to specific tabs
  document.addEventListener('DOMContentLoaded', function() {
      const hash = window.location.hash;

      if (hash === '#remote-credentials') {
          // Show remote credentials tab
          showKeyTypeTab('remote');
      } else if (hash === '#workspace-ssh') {
          showKeyTypeTab('workspace');
      } else if (hash === '#git-ssh') {
          showKeyTypeTab('git');
      } else if (hash === '#gpg-keys') {
          showKeyTypeTab('gpg');
      }
      // If no hash, default (workspace) tab is already shown
  });
