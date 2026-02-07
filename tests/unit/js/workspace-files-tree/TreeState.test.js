/**
 * TreeStateManager Unit Tests
 * Tests state persistence, expansion/collapse, and selection logic
 */

// Mock localStorage for tests
const localStorageMock = (() => {
  let store = {};
  return {
    getItem: jest.fn((key) => store[key] || null),
    setItem: jest.fn((key, value) => { store[key] = value; }),
    removeItem: jest.fn((key) => { delete store[key]; }),
    clear: jest.fn(() => { store = {}; }),
  };
})();

Object.defineProperty(global, 'localStorage', { value: localStorageMock });

// Mock window.addEventListener for storage events
const storageListeners = [];
global.window = {
  addEventListener: jest.fn((event, callback) => {
    if (event === 'storage') {
      storageListeners.push(callback);
    }
  }),
};

// Simplified TreeStateManager for testing
class TreeStateManager {
  constructor(username, slug, mode = 'all') {
    this.mode = mode;
    this.projectKey = `scitex_workspace_tree_${username}_${slug}_${mode}`;
    this.state = this.loadState();
    this.listeners = new Set();
  }

  loadState() {
    try {
      const stored = localStorage.getItem(this.projectKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        return {
          expandedPaths: new Set(parsed.expandedPaths || []),
          selectedPath: parsed.selectedPath || null,
          selectedPaths: new Set(parsed.selectedPaths || []),
          targetPaths: new Set(parsed.targetPaths || []),
          scrollTop: parsed.scrollTop || 0,
          focusPathPerMode: parsed.focusPathPerMode || {
            console: null, vis: null, writer: null, scholar: null, all: null,
          },
          lastClickedPath: null,
        };
      }
    } catch (err) {
      // Ignore
    }
    return {
      expandedPaths: new Set(),
      selectedPath: null,
      selectedPaths: new Set(),
      targetPaths: new Set(),
      scrollTop: 0,
      focusPathPerMode: { console: null, vis: null, writer: null, scholar: null, all: null },
      lastClickedPath: null,
    };
  }

  saveState() {
    try {
      const serializable = {
        expandedPaths: Array.from(this.state.expandedPaths),
        selectedPath: this.state.selectedPath,
        selectedPaths: Array.from(this.state.selectedPaths),
        targetPaths: Array.from(this.state.targetPaths),
        scrollTop: this.state.scrollTop,
        focusPathPerMode: this.state.focusPathPerMode,
      };
      localStorage.setItem(this.projectKey, JSON.stringify(serializable));
    } catch (err) {
      // Ignore
    }
  }

  notifyListeners() {
    this.listeners.forEach((listener) => listener(this.state));
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  getState() {
    return this.state;
  }

  isExpanded(path) {
    return this.state.expandedPaths.has(path);
  }

  expand(path) {
    this.state.expandedPaths.add(path);
    this.saveState();
    this.notifyListeners();
  }

  collapse(path) {
    this.state.expandedPaths.delete(path);
    this.saveState();
    this.notifyListeners();
  }

  toggle(path) {
    const isExpanded = this.isExpanded(path);
    if (isExpanded) {
      this.collapse(path);
    } else {
      this.expand(path);
    }
    return !isExpanded;
  }

  getExpanded() {
    return new Set(this.state.expandedPaths);
  }

  setSelected(path) {
    this.state.selectedPath = path;
    this.saveState();
    this.notifyListeners();
  }

  getSelected() {
    return this.state.selectedPath;
  }

  isSelected(path) {
    return this.state.selectedPaths.has(path);
  }

  addToSelection(path) {
    this.state.selectedPaths.add(path);
    this.state.lastClickedPath = path;
    this.saveState();
    this.notifyListeners();
  }

  removeFromSelection(path) {
    this.state.selectedPaths.delete(path);
    this.saveState();
    this.notifyListeners();
  }

  toggleSelection(path) {
    if (this.state.selectedPaths.has(path)) {
      this.state.selectedPaths.delete(path);
    } else {
      this.state.selectedPaths.add(path);
    }
    this.state.lastClickedPath = path;
    this.saveState();
    this.notifyListeners();
  }

  getSelectedPaths() {
    return new Set(this.state.selectedPaths);
  }

  setSelectedPaths(paths) {
    this.state.selectedPaths = new Set(paths);
    this.saveState();
    this.notifyListeners();
  }

  clearSelection() {
    this.state.selectedPaths.clear();
    this.state.selectedPath = null;
    this.state.lastClickedPath = null;
    this.saveState();
    this.notifyListeners();
  }

  getLastClickedPath() {
    return this.state.lastClickedPath;
  }

  setLastClickedPath(path) {
    this.state.lastClickedPath = path;
  }

  selectSingle(path) {
    this.state.selectedPaths.clear();
    this.state.selectedPaths.add(path);
    this.state.selectedPath = path;
    this.state.lastClickedPath = path;
    this.saveState();
    this.notifyListeners();
  }

  setScrollTop(scrollTop) {
    this.state.scrollTop = scrollTop;
    this.saveState();
  }

  getScrollTop() {
    return this.state.scrollTop;
  }

  expandToPath(filePath) {
    const parts = filePath.split('/');
    let currentPath = '';
    for (let i = 0; i < parts.length - 1; i++) {
      currentPath = currentPath ? `${currentPath}/${parts[i]}` : parts[i];
      this.state.expandedPaths.add(currentPath);
    }
    this.saveState();
    this.notifyListeners();
  }

  isTarget(path) {
    return this.state.targetPaths.has(path);
  }

  addTarget(path) {
    this.state.targetPaths.add(path);
    this.saveState();
    this.notifyListeners();
  }

  removeTarget(path) {
    this.state.targetPaths.delete(path);
    this.saveState();
    this.notifyListeners();
  }

  setTargets(paths) {
    this.state.targetPaths = new Set(paths);
    this.saveState();
    this.notifyListeners();
  }

  clearTargets() {
    this.state.targetPaths.clear();
    this.saveState();
    this.notifyListeners();
  }

  getTargets() {
    return new Set(this.state.targetPaths);
  }

  clear() {
    this.state = {
      expandedPaths: new Set(),
      selectedPath: null,
      selectedPaths: new Set(),
      targetPaths: new Set(),
      scrollTop: 0,
      focusPathPerMode: { console: null, vis: null, writer: null, scholar: null, all: null },
      lastClickedPath: null,
    };
    localStorage.removeItem(this.projectKey);
    this.notifyListeners();
  }
}

describe('TreeStateManager', () => {
  let manager;

  beforeEach(() => {
    localStorageMock.clear();
    jest.clearAllMocks();
    manager = new TreeStateManager('user1', 'project1', 'code');
  });

  describe('constructor', () => {
    it('should create storage key from username, slug, and mode', () => {
      expect(manager.projectKey).toBe('scitex_workspace_tree_user1_project1_code');
    });

    it('should initialize with empty state when no stored data', () => {
      const state = manager.getState();
      expect(state.expandedPaths.size).toBe(0);
      expect(state.selectedPath).toBeNull();
      expect(state.selectedPaths.size).toBe(0);
    });

    it('should load stored state from localStorage', () => {
      localStorageMock.setItem('scitex_workspace_tree_user2_project2_vis', JSON.stringify({
        expandedPaths: ['src', 'src/components'],
        selectedPath: 'src/index.ts',
        selectedPaths: ['src/index.ts'],
        targetPaths: [],
        scrollTop: 100,
      }));

      const newManager = new TreeStateManager('user2', 'project2', 'vis');
      expect(newManager.isExpanded('src')).toBe(true);
      expect(newManager.isExpanded('src/components')).toBe(true);
      expect(newManager.getSelected()).toBe('src/index.ts');
      expect(newManager.getScrollTop()).toBe(100);
    });
  });

  describe('expansion', () => {
    it('should expand a path', () => {
      manager.expand('src');
      expect(manager.isExpanded('src')).toBe(true);
      expect(localStorageMock.setItem).toHaveBeenCalled();
    });

    it('should collapse a path', () => {
      manager.expand('src');
      manager.collapse('src');
      expect(manager.isExpanded('src')).toBe(false);
    });

    it('should toggle expansion', () => {
      expect(manager.toggle('src')).toBe(true); // Now expanded
      expect(manager.isExpanded('src')).toBe(true);

      expect(manager.toggle('src')).toBe(false); // Now collapsed
      expect(manager.isExpanded('src')).toBe(false);
    });

    it('should get all expanded paths', () => {
      manager.expand('src');
      manager.expand('src/components');
      const expanded = manager.getExpanded();
      expect(expanded.has('src')).toBe(true);
      expect(expanded.has('src/components')).toBe(true);
      expect(expanded.size).toBe(2);
    });
  });

  describe('expandToPath', () => {
    it('should expand all parent directories', () => {
      manager.expandToPath('src/components/Button/index.tsx');

      expect(manager.isExpanded('src')).toBe(true);
      expect(manager.isExpanded('src/components')).toBe(true);
      expect(manager.isExpanded('src/components/Button')).toBe(true);
      // File itself should not be expanded
      expect(manager.isExpanded('src/components/Button/index.tsx')).toBe(false);
    });
  });

  describe('selection', () => {
    it('should set selected path', () => {
      manager.setSelected('src/index.ts');
      expect(manager.getSelected()).toBe('src/index.ts');
    });

    it('should allow null selection', () => {
      manager.setSelected('src/index.ts');
      manager.setSelected(null);
      expect(manager.getSelected()).toBeNull();
    });
  });

  describe('multi-selection', () => {
    it('should add to selection', () => {
      manager.addToSelection('src/a.ts');
      manager.addToSelection('src/b.ts');

      expect(manager.isSelected('src/a.ts')).toBe(true);
      expect(manager.isSelected('src/b.ts')).toBe(true);
      expect(manager.getLastClickedPath()).toBe('src/b.ts');
    });

    it('should remove from selection', () => {
      manager.addToSelection('src/a.ts');
      manager.addToSelection('src/b.ts');
      manager.removeFromSelection('src/a.ts');

      expect(manager.isSelected('src/a.ts')).toBe(false);
      expect(manager.isSelected('src/b.ts')).toBe(true);
    });

    it('should toggle selection', () => {
      manager.toggleSelection('src/a.ts');
      expect(manager.isSelected('src/a.ts')).toBe(true);

      manager.toggleSelection('src/a.ts');
      expect(manager.isSelected('src/a.ts')).toBe(false);
    });

    it('should set multiple paths at once', () => {
      manager.setSelectedPaths(['a.ts', 'b.ts', 'c.ts']);
      expect(manager.getSelectedPaths().size).toBe(3);
    });

    it('should clear all selection', () => {
      manager.addToSelection('src/a.ts');
      manager.addToSelection('src/b.ts');
      manager.setSelected('src/a.ts');

      manager.clearSelection();

      expect(manager.getSelectedPaths().size).toBe(0);
      expect(manager.getSelected()).toBeNull();
      expect(manager.getLastClickedPath()).toBeNull();
    });

    it('should select single item and clear others', () => {
      manager.addToSelection('src/a.ts');
      manager.addToSelection('src/b.ts');

      manager.selectSingle('src/c.ts');

      expect(manager.getSelectedPaths().size).toBe(1);
      expect(manager.isSelected('src/c.ts')).toBe(true);
      expect(manager.getSelected()).toBe('src/c.ts');
    });
  });

  describe('targets', () => {
    it('should add target', () => {
      manager.addTarget('src/main.ts');
      expect(manager.isTarget('src/main.ts')).toBe(true);
    });

    it('should remove target', () => {
      manager.addTarget('src/main.ts');
      manager.removeTarget('src/main.ts');
      expect(manager.isTarget('src/main.ts')).toBe(false);
    });

    it('should set multiple targets', () => {
      manager.setTargets(['a.ts', 'b.ts']);
      expect(manager.getTargets().size).toBe(2);
    });

    it('should clear all targets', () => {
      manager.setTargets(['a.ts', 'b.ts']);
      manager.clearTargets();
      expect(manager.getTargets().size).toBe(0);
    });
  });

  describe('scroll position', () => {
    it('should set and get scroll position', () => {
      manager.setScrollTop(150);
      expect(manager.getScrollTop()).toBe(150);
    });
  });

  describe('subscribe', () => {
    it('should notify listeners on state change', () => {
      const listener = jest.fn();
      manager.subscribe(listener);

      manager.expand('src');

      expect(listener).toHaveBeenCalledTimes(1);
      expect(listener).toHaveBeenCalledWith(manager.getState());
    });

    it('should unsubscribe correctly', () => {
      const listener = jest.fn();
      const unsubscribe = manager.subscribe(listener);

      manager.expand('src');
      expect(listener).toHaveBeenCalledTimes(1);

      unsubscribe();
      manager.expand('lib');
      expect(listener).toHaveBeenCalledTimes(1); // Still 1, not called again
    });
  });

  describe('clear', () => {
    it('should reset all state', () => {
      manager.expand('src');
      manager.setSelected('src/index.ts');
      manager.addToSelection('src/a.ts');
      manager.addTarget('src/main.ts');
      manager.setScrollTop(100);

      manager.clear();

      expect(manager.getExpanded().size).toBe(0);
      expect(manager.getSelected()).toBeNull();
      expect(manager.getSelectedPaths().size).toBe(0);
      expect(manager.getTargets().size).toBe(0);
      expect(manager.getScrollTop()).toBe(0);
      expect(localStorageMock.removeItem).toHaveBeenCalledWith(manager.projectKey);
    });
  });
});
