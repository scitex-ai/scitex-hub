# Writer App Inline JavaScript Audit

**Date:** 2025-11-06
**Purpose:** Identify all inline JavaScript in writer_app templates that should be extracted to TypeScript modules

## Priority Classification

- 🔴 **HIGH**: Large logic blocks (>50 lines) that should definitely be TypeScript
- 🟡 **MEDIUM**: Moderate logic (20-50 lines) that would benefit from TypeScript
- 🟢 **LOW**: Small glue code (<20 lines) or server-side variables that must stay inline
- ⚪ **KEEP**: Must remain inline (Django template variables, CSRF tokens, etc.)

---

## 1. index.html (Main Editor)

### 🔴 HIGH: CodeMirror/Monaco Loader (lines 47-139)
- **Size:** ~90 lines
- **Purpose:** Load CodeMirror without AMD conflicts, then Monaco
- **Extract to:** `apps/writer_app/static/writer_app/ts/loaders/editor-loader.ts`
- **Reason:** Complex logic, reusable, testable

### ⚪ KEEP: WRITER_CONFIG (lines 141-174)
- **Size:** ~30 lines
- **Purpose:** Server-rendered Django config
- **Reason:** Uses Django template tags (`{{ project.id }}`, `{{ user.username }}`)

### ⚪ KEEP: Import Map (lines 177-194)
- **Size:** ~15 lines
- **Purpose:** ES6 module path mappings
- **Reason:** Uses `{% static %}` template tag

---

## 2. collaborative_editor_partials/scripts.html

### 🔴 HIGH: Collaborative Editor Logic (~200+ lines)
- **Purpose:** Editor initialization, collaboration toggle, auto-save, word count
- **Extract to:** `apps/writer_app/static/writer_app/ts/editor/collaborative-editor.ts`
- **Server-side data needed:**
  ```javascript
  currentManuscript = {
      id: {{ manuscript.id }},  // Django template variable
      sections: [...]
  };
  ```
- **Solution:** Pass as data attribute or via window config

---

## 3. latex_editor_partials/preview_panel_partials/preview_scripts.html

### 🔴 HIGH: Preview Panel Logic (~150+ lines)
- **Purpose:** PDF preview, compilation status, auto-compile
- **Extract to:** `apps/writer_app/static/writer_app/ts/editor/preview-panel.ts`
- **Has:** fetch() calls, WebSocket-like polling, DOM manipulation

---

## 4. compilation_view_partials/change_attribution_scripts.html

### 🟡 MEDIUM: Compilation Status Logic (~100 lines)
- **Purpose:** Poll compilation status, handle results
- **Extract to:** `apps/writer_app/static/writer_app/ts/compilation/status-poller.ts`
- **Has:** fetch() calls, progress tracking

---

## 5. version_control_dashboard_partials/modal_create_branch.html

### 🟡 MEDIUM: Version Control Modals (~150 lines)
- **Purpose:** Branch creation, diff viewing, merge requests
- **Extract to:** `apps/writer_app/static/writer_app/ts/version_control/modals.ts`
- **Has:** fetch() calls, form handling, modal management

---

## 6. arxiv/submission.html

### 🟢 LOW: Check for TypeScript compiled version
- **Current:** `<script src="{% static 'writer_app/js/arxiv/submission.js' %}"></script>`
- **TypeScript exists:** Yes - `apps/writer_app/static/writer_app/ts/arxiv/submission.ts`
- **Status:** ✅ Already migrated to TypeScript

---

## 7. collaboration/session.html

### 🟢 LOW: Check for TypeScript compiled version
- **Current:** `<script src="{% static 'writer_app/js/collaboration/session.js' %}"></script>`
- **TypeScript exists:** Yes - `apps/writer_app/static/writer_app/ts/collaboration/session.ts`
- **Status:** ✅ Already migrated to TypeScript

---

## 8. compilation/compilation_view.html

### 🟢 LOW: Check for TypeScript compiled version
- **Current:** `<script src="{% static 'writer_app/js/compilation/compilation.js' %}"></script>`
- **TypeScript exists:** Yes - `apps/writer_app/static/writer_app/ts/compilation/compilation_view.ts`
- **Status:** ✅ Already migrated to TypeScript

---

## 9. editor/editor.html

### 🟢 LOW: Check for TypeScript compiled version
- **Current:** `<script src="{% static 'writer_app/js/editor/editor.js' %}"></script>`
- **TypeScript exists:** Yes - `apps/writer_app/static/writer_app/ts/editor/editor.ts`
- **Status:** ✅ Already migrated to TypeScript

---

## 10. version_control/index.html

### 🟢 LOW: Check for TypeScript compiled version
- **Current:** `<script src="{% static 'writer_app/js/version_control/index.js' %}"></script>`
- **TypeScript exists:** Yes - `apps/writer_app/static/writer_app/ts/version_control/index.ts`
- **Status:** ✅ Already migrated to TypeScript

---

## 11. base/app_base.html

### 🟢 LOW: Utility script reference
- **Current:** `<script src="{% static 'writer_app/js/shared/utils.js' %}"></script>`
- **Check:** Does TypeScript version exist?

---

## Summary

### ✅ COMPLETED - HIGH Priority Extractions

1. **✅ CodeMirror/Monaco Loader** (index.html)
   - **Created:** `loaders/editor-loader.ts` (6.9KB compiled)
   - **Before:** 90 lines inline JavaScript
   - **After:** 10 lines module import
   - **Extracted:** 80 lines → TypeScript module

2. **✅ Collaborative Editor Logic** (collaborative_editor_partials/scripts.html)
   - **Created:** `editor/collaborative-editor-manager.ts` (14KB compiled)
   - **Before:** 319 lines inline JavaScript
   - **After:** 27 lines module import
   - **Extracted:** 292 lines → TypeScript module

3. **✅ Preview Panel Logic** (preview_panel_partials/preview_scripts.html)
   - **Created:** `editor/preview-panel-manager.ts` (12KB compiled)
   - **Before:** 305 lines inline JavaScript
   - **After:** 20 lines module import
   - **Extracted:** 285 lines → TypeScript module

**Total Extracted: 657 lines of inline JavaScript → 3 TypeScript modules (32.9KB compiled)**

### Medium Priority

4. **Extract Compilation Status** (change_attribution_scripts.html)
   - Create: `compilation/status-poller.ts`
   - ~100 lines

5. **Extract Version Control Modals** (modal_create_branch.html)
   - Create: `version_control/modals.ts`
   - ~150 lines

### Already Migrated ✅

- arxiv/submission.ts
- collaboration/session.ts
- compilation/compilation_view.ts
- editor/editor.ts
- version_control/index.ts

### Work Completed (2025-11-06)

- **Total inline JS extracted:** 657 lines → TypeScript modules
- **New TypeScript files created:** 3 (HIGH priority items)
- **Template files cleaned:** 3 files (from 714 lines → 57 lines)
- **Compiled output:** 32.9KB (editor-loader.js + collaborative-editor-manager.js + preview-panel-manager.js)
- **Status:** ✅ All HIGH priority extractions complete

---

## Recommended Approach

1. Start with HIGH priority items (largest impact)
2. Extract to proper TypeScript modules with types
3. Keep server-side data in inline `<script>` blocks as `window.CONFIG`
4. Test each extraction before moving to next
5. Update JAVASCRIPT_TYPESCRIPT_MIGRATION_STATUS.md after completion
