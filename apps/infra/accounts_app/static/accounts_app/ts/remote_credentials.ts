/**
 * Remote credentials page functionality
 */

function toggleAddForm(): void {
  const form = document.getElementById("addCredentialForm");
  if (form) {
    form.classList.toggle("show");
  }
}

function toggleSSHImport(): void {
  const area = document.getElementById("sshConfigImport");
  if (area) {
    area.classList.toggle("show");
  }
}

interface SSHConfigFields {
  host?: string;
  hostname?: string;
  port?: string;
  user?: string;
  identityfile?: string;
}

function parseSSHConfig(text: string): SSHConfigFields {
  const result: SSHConfigFields = {};
  const lines = text.split("\n");

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    // Match "Key Value" or "Key=Value" (case-insensitive)
    const match = trimmed.match(/^(\S+)\s*[=\s]\s*(.+)$/);
    if (!match) continue;

    const key = match[1].toLowerCase();
    const value = match[2].trim();

    switch (key) {
      case "host":
        // Take first alias only (ignore wildcards)
        result.host = value.split(/\s+/)[0];
        break;
      case "hostname":
        result.hostname = value;
        break;
      case "port":
        result.port = value;
        break;
      case "user":
        result.user = value;
        break;
      case "identityfile":
        result.identityfile = value;
        break;
    }
  }

  return result;
}

function parseAndFillSSHConfig(): void {
  const textarea = document.getElementById(
    "ssh_config_text",
  ) as HTMLTextAreaElement | null;
  const status = document.getElementById("sshConfigParseStatus");
  if (!textarea) return;

  const text = textarea.value.trim();
  if (!text) {
    if (status) {
      status.textContent = "Paste an SSH config block first.";
      status.className = "parse-status parse-status-error";
    }
    return;
  }

  const fields = parseSSHConfig(text);
  const filled: string[] = [];

  if (fields.host) {
    setFieldValue("name", fields.host);
    filled.push("Name");
  }
  if (fields.hostname) {
    setFieldValue("ssh_host", fields.hostname);
    filled.push("Host");
  }
  if (fields.port) {
    setFieldValue("ssh_port", fields.port);
    filled.push("Port");
  }
  if (fields.user) {
    setFieldValue("ssh_username", fields.user);
    filled.push("Username");
  }

  if (status) {
    if (filled.length > 0) {
      let msg = `Filled: ${filled.join(", ")}`;
      if (fields.identityfile) {
        msg += ` | Key path: ${fields.identityfile}`;
      }
      status.textContent = msg;
      status.className = "parse-status parse-status-success";
    } else {
      status.textContent = "No recognized fields found. Check format.";
      status.className = "parse-status parse-status-error";
    }
  }
}

function setFieldValue(id: string, value: string): void {
  const el = document.getElementById(id) as HTMLInputElement | null;
  if (el) {
    el.value = value;
  }
}

// Ensure form submission works — use programmatic submit as failsafe
document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector(
    "#addCredentialForm form",
  ) as HTMLFormElement | null;
  if (!form) return;

  const submitBtn = form.querySelector(
    "button[type='submit']",
  ) as HTMLButtonElement | null;
  if (!submitBtn) return;

  // Replace button click with programmatic form.submit() to bypass
  // any global event listeners that might interfere
  submitBtn.addEventListener("click", (e) => {
    e.preventDefault();
    if (form.checkValidity()) {
      form.submit();
    } else {
      form.reportValidity();
    }
  });
});

function switchKeyMode(mode: string): void {
  const generatePanel = document.getElementById("keyModeGenerate");
  const uploadPanel = document.getElementById("keyModeUpload");
  const modeInput = document.getElementById(
    "key_mode",
  ) as HTMLInputElement | null;

  if (modeInput) modeInput.value = mode;

  // Toggle panels
  if (generatePanel) {
    generatePanel.classList.toggle("key-mode-hidden", mode !== "generate");
  }
  if (uploadPanel) {
    uploadPanel.classList.toggle("key-mode-hidden", mode !== "upload");
  }

  // Toggle tab active state
  document.querySelectorAll(".key-mode-tab").forEach((tab) => {
    const el = tab as HTMLElement;
    el.classList.toggle("active", el.dataset.mode === mode);
  });
}

// Export for inline onclick handlers
(window as any).toggleAddForm = toggleAddForm;
(window as any).toggleSSHImport = toggleSSHImport;
(window as any).parseAndFillSSHConfig = parseAndFillSSHConfig;
(window as any).switchKeyMode = switchKeyMode;
