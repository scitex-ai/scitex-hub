/**
 * Centralized URL registry for all API and navigation endpoints.
 * Import from here instead of hardcoding URL strings in fetch() calls.
 *
 * Convention: kebab-case paths, grouped by app module.
 */

export const API_URLS = {
  // --- Core API ---
  server: {
    health: "/api/server-health/",
  },
  project: {
    switch: "/api/project/switch/",
    create: "/api/project/create/",
    list: "/api/project/list/",
    checkName: "/api/project/check-name/",
  },
  visitor: {
    heartbeat: "/api/visitor/heartbeat/",
  },
  // --- Hub ---
  hub: {
    setActiveProject: "/apps/home/api/set-active-project/",
    updateTopics: "/apps/home/api/update-topics/",
  },
  // --- Accounts ---
  accounts: {
    aiLimits: "/accounts/api/ai-limits/",
    autoResponsePrefs: "/accounts/api/auto-response-prefs/",
  },
  // --- Apps API ---
  apps: {
    reorder: "/apps/api/reorder/",
  },
  // --- LLM ---
  llm: {
    providers: "/apps/llm/api/providers/",
    model: "/apps/llm/api/model/",
    chatStream: "/apps/llm/api/chat/stream/",
    upload: "/apps/llm/api/upload/",
    tts: "/apps/llm/api/tts/",
    stt: "/apps/llm/api/stt/",
    sttModels: "/apps/llm/api/stt/models/",
    bash: "/apps/llm/api/bash/",
    sessions: "/apps/llm/api/sessions/",
  },
  // --- Console ---
  console: {
    jobs: "/apps/console/api/jobs/",
  },
  // --- Scholar ---
  scholar: {
    recentJobs: "/apps/scholar/api/bibtex/recent-jobs/",
    savePaper: "/apps/scholar/api/save-paper/",
    pdfDownload: "/apps/scholar/api/pdf/download/",
    libraryPapers: "/apps/scholar/api/library/papers/",
    libraryBridge: "/apps/scholar/api/library/bridge/",
    sourcePreferences: "/apps/scholar/api/source-preferences/",
    saveSearch: "/apps/scholar/api/save-search/",
    autoSaveLibrary: "/apps/scholar/api/auto-save-library/",
    exportBibtex: "/apps/scholar/api/export/bibtex/",
  },
  // --- Vis ---
  vis: {
    editorPreview: "/apps/vis/api/editor/preview/",
    editorLoad: "/apps/vis/api/editor/load/",
    editorSave: "/apps/vis/api/editor/save/",
    editorExport: "/apps/vis/api/editor/export/",
    galleryAvailable: "/apps/vis/api/gallery/available/",
    galleryProject: "/apps/vis/api/gallery/project/",
    galleryAdd: "/apps/vis/api/gallery/add/",
    plotMetadata: "/apps/vis/api/plot/metadata/",
    bundlesPltz: "/apps/vis/api/bundles/pltz/",
    bundlesFigz: "/apps/vis/api/bundles/figz/",
    bundleCreate: "/apps/vis/api/bundles/create/",
    bundleSave: "/apps/vis/api/bundles/save/",
    canvasTab: "/apps/vis/api/canvas/tab/",
    presets: "/apps/vis/api/presets/",
  },
  // --- Stats (public tools) ---
  stats: {
    base: "/api/stats/",
  },
  // --- Writer ---
  writer: {
    sectionsConfig: "/apps/writer/api/sections-config/",
    initializeWorkspace: "/apps/writer/api/initialize-workspace/",
  },
  // --- Clew ---
  clew: {
    base: "/apps/clew/api/",
  },
  // --- On-site capture (Console) ---
  onSiteCapture: {
    screenshot: "/apps/console/api/on-site/screenshot/",
    evaluate: "/apps/console/api/on-site/evaluate/",
    capture: "/apps/console/api/on-site/capture/",
  },
} as const;

/**
 * Navigation URLs for window.location.href assignments.
 */
export const NAV_URLS = {
  scholar: {
    index: "/apps/scholar/",
    library: "/apps/scholar/#library",
  },
  console: {
    index: "/apps/console/",
    workspace: "/apps/console/workspace/",
  },
  vis: {
    index: "/apps/vis/",
  },
  writer: {
    index: "/apps/writer/",
    project: (projectId: number | string) =>
      `/apps/writer/project/${projectId}/`,
  },
  visitorExpired: "/visitor-expired/",
} as const;

// EOF
