"""React/Vite/Zustand template generators for the SciTeX app scaffold."""

from __future__ import annotations

import json


def _package_json(name, label):
    pkg = {
        "name": name.replace("_", "-"),
        "version": "0.1.0",
        "private": True,
        "description": f"React frontend for {label}",
        "scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview",
        },
        "dependencies": {
            "react": "^18.3.0",
            "react-dom": "^18.3.0",
            "zustand": "^4.5.0",
            "@scitex/ui": "file:../../scitex-ui",
        },
        "devDependencies": {
            "@types/react": "^18.3.0",
            "@types/react-dom": "^18.3.0",
            "@vitejs/plugin-react": "^4.3.0",
            "typescript": "^5.5.0",
            "vite": "^5.4.0",
        },
    }
    return json.dumps(pkg, indent=2, ensure_ascii=False) + "\n"


def _vite_config_ts(name):
    static_out = f"../static/{name}/js"
    return f"""import {{ execSync }} from "child_process";
import {{ defineConfig }} from "vite";
import react from "@vitejs/plugin-react";

/**
 * Discover scitex-ui static directory from the Python environment.
 * Works for both pip-installed packages and editable (dev) installs.
 */
function discoverScitexUiStatic(): string | null {{
  if (process.env.SCITEX_UI_STATIC) return process.env.SCITEX_UI_STATIC;
  try {{
    return execSync(
      'python3 -c "import scitex_ui; print(scitex_ui.get_static_dir())"',
      {{ encoding: "utf-8", timeout: 5000 }},
    ).trim();
  }} catch {{
    return null;
  }}
}}

const SCITEX_UI_STATIC = discoverScitexUiStatic();

// https://vitejs.dev/config/
export default defineConfig({{
  plugins: [react()],
  resolve: {{
    alias: {{
      ...(SCITEX_UI_STATIC ? {{ "scitex-ui": SCITEX_UI_STATIC }} : {{}}),
    }},
  }},
  build: {{
    outDir: "{static_out}",
    emptyOutDir: true,
    rollupOptions: {{
      input: "src/main.tsx",
      output: {{
        entryFileNames: "main.js",
        chunkFileNames: "[name].js",
        assetFileNames: "[name][extname]",
      }},
    }},
  }},
  server: {{
    fs: {{
      allow: [".", ...(SCITEX_UI_STATIC ? [SCITEX_UI_STATIC] : [])],
    }},
  }},
}});
"""


def _tsconfig_json():
    cfg = {
        "compilerOptions": {
            "target": "ES2020",
            "useDefineForClassFields": True,
            "lib": ["ES2020", "DOM", "DOM.Iterable"],
            "module": "ESNext",
            "skipLibCheck": True,
            "moduleResolution": "bundler",
            "allowImportingTsExtensions": True,
            "isolatedModules": True,
            "moduleDetection": "force",
            "noEmit": True,
            "jsx": "react-jsx",
            "strict": True,
        },
        "include": ["src"],
    }
    return json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"


def _main_tsx(name):
    return f"""import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

const rootEl = document.getElementById("{name}-root");
if (!rootEl) {{
  throw new Error("Mount point #{name}-root not found in DOM.");
}}

ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
"""


def _app_tsx(name, label, icon):
    return f"""import React from "react";
import {{ useAppStore }} from "./store/useAppStore";

export default function App() {{
  const {{ count, increment }} = useAppStore();

  return (
    <div
      style={{{{
        fontFamily: "inherit",
        color: "var(--text-primary)",
        background: "var(--workspace-bg-secondary)",
        border: "1px solid var(--workspace-border-default)",
        borderRadius: "6px",
        padding: "2rem",
      }}}}
    >
      <h3 style={{{{ marginTop: 0, color: "var(--text-primary)" }}}}>
        <i className="{icon}" style={{{{ marginRight: "0.5rem" }}}} />
        {label} — React
      </h3>
      <p style={{{{ color: "var(--text-secondary)" }}}}>
        This component is rendered by React. Edit{" "}
        <code>frontend/src/App.tsx</code> to get started.
      </p>
      <div style={{{{ marginTop: "1rem" }}}}>
        <button
          onClick={{increment}}
          style={{{{
            background: "var(--accent-primary, #4a9eff)",
            color: "#fff",
            border: "none",
            borderRadius: "4px",
            padding: "0.4rem 1rem",
            cursor: "pointer",
          }}}}
        >
          Clicked {{count}} time{{count !== 1 ? "s" : ""}}
        </button>
      </div>
    </div>
  );
}}
"""


def _use_app_store_ts(label):
    return f"""import {{ create }} from "zustand";

interface AppState {{
  /** Example counter — replace with real state. */
  count: number;
  /** Increment the counter. */
  increment: () => void;
  /** Reset the counter. */
  reset: () => void;
}}

/**
 * Global state store for {label}.
 *
 * Replace this template with your actual application state.
 */
export const useAppStore = create<AppState>((set) => ({{
  count: 0,
  increment: () => set((s) => ({{ count: s.count + 1 }})),
  reset: () => set({{ count: 0 }}),
}}));
"""


def build_react_files(name, label, icon):
    """Return dict of relpath -> content for React frontend files."""
    return {
        "frontend/package.json": _package_json(name, label),
        "frontend/vite.config.ts": _vite_config_ts(name),
        "frontend/tsconfig.json": _tsconfig_json(),
        "frontend/src/main.tsx": _main_tsx(name),
        "frontend/src/App.tsx": _app_tsx(name, label, icon),
        "frontend/src/store/useAppStore.ts": _use_app_store_ts(label),
    }


# EOF
