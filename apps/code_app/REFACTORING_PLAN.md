# Code Workspace Refactoring Plan

## Current State Analysis

**File:** `apps/code_app/static/code_app/ts/workspace/index.ts`
- **Lines:** 607 (2x over 300-line threshold)
- **Violation:** Critical - exceeds file size limits from RULES/06_FILE_SIZE_LIMITS.md
- **Status:** ⚠️ REQUIRES IMMEDIATE REFACTORING

## Rule Violations

### 1. File Size Limit (RULES/06_FILE_SIZE_LIMITS.md)
- ❌ **Current:** 607 lines
- ✅ **Target:** <300 lines per file
- **Priority:** HIGH (2x threshold)

### 2. Single Responsibility (RULES/00_DJANGO_ORGANIZATION_FULLSTACK.md)
- ❌ WorkspaceOrchestrator does too much (20 methods)
- ✅ Should be split into feature-focused modules

## Current Method Breakdown

### WorkspaceOrchestrator (607 lines, 20 methods)

**Initialization (5 methods, ~150 lines):**
- `constructor()` - Dependency injection
- `init()` - Async initialization
- `setupThemeListeners()` - Theme change handling
- `initScratchBuffer()` - Scratch buffer setup
- `attachEventListeners()` - Global keyboard shortcuts

**File State Management (5 methods, ~200 lines):**
- `handleFileClick()` - File tree click handler
- `loadFile()` - Fetch and open file
- `switchToFile()` - Switch active file
- `closeTab()` - Close file tab
- `saveFile()` - Save current file

**File Commands (5 methods, ~150 lines):**
- `handleContextMenuAction()` - Context menu dispatcher
- `createNewFile()` - Create file at root
- `createNewFolder()` - Create folder at root
- `renameFile()` - Rename file/folder
- `deleteFile()` - Delete file/folder

**Public API (2 methods, ~50 lines):**
- `createFileInFolder()` - Create file in specific folder
- `createFolderInFolder()` - Create folder in specific folder

**Visitor/Auth (3 methods, ~50 lines):**
- `isVisitor()` - Check if current user is visitor
- `showSignupWarning()` - Show signup modal
- `showVisitorWarningOnce()` - Show toast once

**Utility (1 method, ~7 lines):**
- `getScratchContent()` - Generate scratch buffer content

## Refactoring Strategy

### Phase 1: Extract File State Management
**New file:** `workspace/files/FileStateManager.ts` (~200 lines)

**Responsibilities:**
- Manage `openFiles` Map
- Handle file loading and switching
- Track current file state
- Handle tab closure

**Methods to extract:**
- `loadFile()`
- `switchToFile()`
- `closeTab()`
- `handleFileClick()` (delegates to loadFile)

**Benefits:**
- Single responsibility: file state
- Clear interface for file operations
- Easier testing

### Phase 2: Extract File Command Handler
**New file:** `workspace/files/FileCommandHandler.ts` (~150 lines)

**Responsibilities:**
- Handle file/folder CRUD operations
- Context menu action dispatching
- Visitor permission checks

**Methods to extract:**
- `handleContextMenuAction()`
- `createNewFile()`
- `createNewFolder()`
- `renameFile()`
- `deleteFile()`
- `createFileInFolder()` (public API)
- `createFolderInFolder()` (public API)

**Benefits:**
- Encapsulates all file commands
- Clear permission boundary
- Reusable for different UIs

### Phase 3: Extract Visitor/Auth Manager
**New file:** `workspace/auth/VisitorManager.ts` (~80 lines)

**Responsibilities:**
- Visitor detection
- Permission enforcement
- Warning/modal display

**Methods to extract:**
- `isVisitor()`
- `showSignupWarning()`
- `showVisitorWarningOnce()`

**Static utility or singleton:**
```typescript
export class VisitorManager {
  private static warningShown = false;
  private config: EditorConfig;

  constructor(config: EditorConfig) {
    this.config = config;
  }

  isVisitor(): boolean {
    return this.config.currentProject?.owner.startsWith("visitor-") || false;
  }

  requireAuth(action: string): boolean {
    if (this.isVisitor()) {
      this.showSignupWarning();
      return false;
    }
    return true;
  }

  showSignupWarning(): void { /* ... */ }
  showVisitorWarningOnce(): void { /* ... */ }
}
```

**Benefits:**
- Clear permission model
- Reusable across workspace
- Easy to test and mock

### Phase 4: Extract Initialization
**New file:** `workspace/core/WorkspaceInitializer.ts` (~150 lines)

**Responsibilities:**
- Coordinate async initialization
- Setup theme listeners
- Initialize scratch buffer
- Attach global event listeners

**Methods to extract:**
- `init()`
- `setupThemeListeners()`
- `initScratchBuffer()`
- `getScratchContent()`
- `attachEventListeners()`

**Pattern:**
```typescript
export class WorkspaceInitializer {
  constructor(
    private monacoManager: MonacoManager,
    private ptyManager: PTYManager,
    private fileTreeManager: FileTreeManager,
    private config: EditorConfig
  ) {}

  async initialize(): Promise<void> {
    await this.setupUI();
    await this.loadInitialContent();
    this.setupEventListeners();
    this.setupThemeListeners();
  }
}
```

**Benefits:**
- Clear initialization sequence
- Easier to add new init steps
- Testable in isolation

## Final Structure

```
apps/code_app/static/code_app/ts/workspace/
├── index.ts (~150 lines)                      # Main orchestrator
│   └── WorkspaceOrchestrator                  # Wires everything together
│
├── core/
│   ├── types.ts                               # Existing
│   └── WorkspaceInitializer.ts (~150 lines)   # NEW - Initialization logic
│
├── files/
│   ├── FileStateManager.ts (~200 lines)       # NEW - File state & switching
│   ├── FileCommandHandler.ts (~150 lines)     # NEW - File CRUD operations
│   ├── FileOperations.ts                      # Existing - API calls
│   ├── FileTabManager.ts                      # Existing - Tab UI
│   └── FileTreeManager.ts                     # Existing - Tree UI
│
├── auth/
│   └── VisitorManager.ts (~80 lines)          # NEW - Visitor permissions
│
├── editor/
│   └── MonacoManager.ts                       # Existing
│
├── terminal/
│   └── PTYManager.ts                          # Existing
│
├── git/
│   ├── GitOperations.ts                       # Existing
│   └── GitStatusManager.ts                    # Existing
│
└── ui/
    └── UIComponents.ts                        # Existing
```

## Implementation Plan

### Step 1: Create VisitorManager (Smallest, Safest)
**Time:** 30 minutes
**Risk:** LOW

1. Create `workspace/auth/VisitorManager.ts`
2. Move visitor-related methods
3. Update WorkspaceOrchestrator to use VisitorManager
4. Compile and test

**Validation:**
- Visitor warnings still work
- Permission checks work correctly
- No duplicate logic

### Step 2: Create FileStateManager
**Time:** 1 hour
**Risk:** MEDIUM

1. Create `workspace/files/FileStateManager.ts`
2. Move file state methods
3. Expose clean interface: `openFile()`, `switchFile()`, `closeFile()`
4. Update WorkspaceOrchestrator
5. Compile and test

**Validation:**
- File opening/closing works
- Tab switching works
- State is maintained correctly
- Monaco editor shows correct content

### Step 3: Create FileCommandHandler
**Time:** 1 hour
**Risk:** MEDIUM

1. Create `workspace/files/FileCommandHandler.ts`
2. Move command methods
3. Inject VisitorManager for permission checks
4. Update WorkspaceOrchestrator
5. Compile and test

**Validation:**
- Create/rename/delete work
- Context menu works
- Folder operations work
- Visitor blocking works

### Step 4: Create WorkspaceInitializer
**Time:** 45 minutes
**Risk:** LOW

1. Create `workspace/core/WorkspaceInitializer.ts`
2. Move initialization methods
3. Keep WorkspaceOrchestrator.init() as thin wrapper
4. Compile and test

**Validation:**
- Workspace initializes correctly
- Scratch buffer loads
- Theme switching works
- Event listeners attached

### Step 5: Refactor WorkspaceOrchestrator
**Time:** 30 minutes
**Risk:** LOW

1. Simplify to pure orchestration
2. Constructor injects all managers
3. Delegates to specialized managers
4. Compile and test

**Final WorkspaceOrchestrator (~150 lines):**
```typescript
export class WorkspaceOrchestrator {
  private config: EditorConfig;

  // Existing managers
  private monacoManager: MonacoManager;
  private ptyManager: PTYManager;
  private fileTreeManager: FileTreeManager;
  private fileOperations: FileOperations;
  private fileTabManager: FileTabManager;
  private gitStatusManager: GitStatusManager;
  private gitOperations: GitOperations;
  private uiComponents: UIComponents;

  // NEW managers
  private fileStateManager: FileStateManager;
  private fileCommandHandler: FileCommandHandler;
  private visitorManager: VisitorManager;
  private initializer: WorkspaceInitializer;

  constructor(config: EditorConfig) {
    this.config = config;

    // Initialize managers
    this.monacoManager = new MonacoManager(config);
    this.ptyManager = new PTYManager(config);
    // ... existing managers

    // NEW managers
    this.visitorManager = new VisitorManager(config);
    this.fileStateManager = new FileStateManager(
      this.monacoManager,
      this.fileOperations,
      this.fileTabManager
    );
    this.fileCommandHandler = new FileCommandHandler(
      config,
      this.fileOperations,
      this.fileTreeManager,
      this.visitorManager
    );
    this.initializer = new WorkspaceInitializer(
      this.monacoManager,
      this.ptyManager,
      this.fileTreeManager,
      this.fileStateManager,
      config
    );

    // Start initialization
    this.initializer.initialize().catch(err => {
      console.error("[WorkspaceOrchestrator] Initialization failed:", err);
    });
  }

  // Public API (delegates to managers)
  public async createFileInFolder(folderPath: string): Promise<void> {
    return this.fileCommandHandler.createFileInFolder(folderPath);
  }

  public async createFolderInFolder(parentPath: string): Promise<void> {
    return this.fileCommandHandler.createFolderInFolder(parentPath);
  }
}
```

## Success Criteria

### Quantitative
- ✅ All files <300 lines
- ✅ WorkspaceOrchestrator ~150 lines (75% reduction)
- ✅ 4 new focused modules created
- ✅ No duplicate code
- ✅ All tests pass

### Qualitative
- ✅ Clear responsibility boundaries
- ✅ Easy to understand each module
- ✅ Easy to test in isolation
- ✅ Easy to add new features
- ✅ Follows project conventions

## Testing Strategy

### Unit Tests
- Test each manager in isolation
- Mock dependencies
- Test edge cases

### Integration Tests
- Test WorkspaceOrchestrator wiring
- Test file operations end-to-end
- Test visitor permission flows

### Manual Testing
1. Open workspace
2. Create/rename/delete files
3. Switch between files
4. Test as visitor
5. Test theme switching

## Rollback Plan

If issues arise:
1. Keep old `workspace/index.ts` as `workspace/index.ts.backup`
2. Git commit after each step
3. Can revert individual commits
4. Can switch back to backup file

## Timeline

**Total time:** ~4 hours
**Recommended approach:** Incremental over 2 days

- Day 1 Morning: Steps 1-2 (VisitorManager + FileStateManager)
- Day 1 Afternoon: Step 3 (FileCommandHandler)
- Day 2 Morning: Steps 4-5 (Initializer + Orchestrator cleanup)
- Day 2 Afternoon: Testing and documentation

## Post-Refactoring Benefits

1. **Maintainability:** Clear where to add new features
2. **Testability:** Each module testable in isolation
3. **Readability:** Obvious what each module does
4. **Reusability:** Managers can be used elsewhere
5. **Compliance:** Follows all project rules
6. **Performance:** No impact (same runtime behavior)
7. **Extensibility:** Easy to add new file operations

## Next Steps After This Refactoring

1. Add unit tests for new managers
2. Document public APIs in each manager
3. Update code_app documentation
4. Consider similar refactoring for other large files:
   - `vis_app/ts/editor.ts` (7,630 lines!)
   - `writer_app/ts/index.ts` (4,599 lines)

---

**Status:** READY TO IMPLEMENT
**Approval:** Awaiting user confirmation to proceed
