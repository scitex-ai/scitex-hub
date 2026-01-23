/**
 * Account Switcher TypeScript
 * Handles multi-account switching functionality
 */

interface Account {
  user_id: number;
  username: string;
  full_name?: string;
}

interface AuthenticatedAccountsResponse {
  accounts: Account[];
  current_user_id: number;
}

function initializeAccountSwitcher(): void {
  const accountSwitcher = document.getElementById("account-switcher") as HTMLSelectElement;
  const accountSwitcherDropdownWrapper = document.getElementById(
    "account-switcher-dropdown-wrapper"
  ) as HTMLElement;

  if (accountSwitcher) {
    // Load authenticated accounts
    fetch("/auth/api/authenticated-accounts/")
      .then((response) => response.json())
      .then((data: AuthenticatedAccountsResponse) => {
        const accounts = data.accounts || [];
        const currentUserId = data.current_user_id;

        if (accounts.length <= 1) {
          // Hide dropdown selector if only one account, but keep "Add another account" visible
          if (accountSwitcherDropdownWrapper) {
            accountSwitcherDropdownWrapper.style.display = "none";
          }
          return;
        }

        // Show dropdown wrapper
        if (accountSwitcherDropdownWrapper) {
          accountSwitcherDropdownWrapper.style.display = "block";
        }

        accountSwitcher.innerHTML =
          '<option value="">-- Switch to --</option>';
        accounts.forEach((account) => {
          const isCurrentUser = account.user_id === currentUserId;
          const displayName = account.full_name || account.username;

          const option = document.createElement("option");
          option.value = String(account.user_id);
          option.textContent = `${displayName} ${isCurrentUser ? "(current)" : ""}`;
          option.disabled = isCurrentUser;
          accountSwitcher.appendChild(option);
        });

        // Handle account switch
        accountSwitcher.addEventListener("change", function (this: HTMLSelectElement) {
          const userId = this.value;
          if (userId) {
            const currentUrl = window.location.href;
            window.location.href = `/auth/switch/${userId}/?next=${encodeURIComponent(currentUrl)}`;
          }
        });
      })
      .catch((err) => {
        console.error("Failed to load authenticated accounts:", err);
        if (accountSwitcherDropdownWrapper) {
          accountSwitcherDropdownWrapper.style.display = "none";
        }
      });
  }
}

// Initialize immediately if DOM is ready, otherwise wait
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeAccountSwitcher);
} else {
  initializeAccountSwitcher();
}
