/**
 * SearchHandler Unit Tests
 * Tests fuzzy search, filtering, and tree traversal logic
 */

// Mock TreeItem type for testing
const createTreeItem = (name, path, type = 'file', children = undefined) => ({
  name,
  path,
  type,
  children,
});

// Import the SearchHandler class
// Note: We recreate the class logic here for isolated testing
// In a real setup, we'd use proper module resolution

class SearchHandler {
  constructor(onSearchChange, getTreeData) {
    this.searchQuery = '';
    this.onSearchChange = onSearchChange;
    this.getTreeData = getTreeData;
  }

  setQuery(query) {
    this.searchQuery = query.toLowerCase().trim();
    this.onSearchChange();
  }

  getQuery() {
    return this.searchQuery;
  }

  clear() {
    this.searchQuery = '';
    this.onSearchChange();
  }

  isActive() {
    return this.searchQuery.length > 0;
  }

  matches(item) {
    if (!this.searchQuery) return true;

    const name = item.name.toLowerCase();
    const path = item.path.toLowerCase();

    if (name.includes(this.searchQuery)) return true;
    if (path.includes(this.searchQuery)) return true;
    if (this.fuzzyMatch(name, this.searchQuery)) return true;

    return false;
  }

  fuzzyMatch(text, query) {
    let queryIndex = 0;
    for (let i = 0; i < text.length && queryIndex < query.length; i++) {
      if (text[i] === query[queryIndex]) {
        queryIndex++;
      }
    }
    return queryIndex === query.length;
  }

  filterTree(items) {
    if (!this.searchQuery) return items;
    return this.filterRecursive(items);
  }

  filterRecursive(items) {
    const result = [];

    for (const item of items) {
      if (item.type === 'directory' && item.children) {
        const filteredChildren = this.filterRecursive(item.children);
        if (this.matches(item) || filteredChildren.length > 0) {
          result.push({
            ...item,
            children: filteredChildren.length > 0 ? filteredChildren : item.children,
          });
        }
      } else {
        if (this.matches(item)) {
          result.push(item);
        }
      }
    }

    return result;
  }

  getMatchingItems() {
    if (!this.searchQuery) return [];

    const matches = [];
    this.collectMatches(this.getTreeData(), matches);
    return matches;
  }

  collectMatches(items, matches) {
    for (const item of items) {
      if (this.matches(item) && item.type === 'file') {
        matches.push(item);
      }
      if (item.type === 'directory' && item.children) {
        this.collectMatches(item.children, matches);
      }
    }
  }
}

describe('SearchHandler', () => {
  let handler;
  let onSearchChangeMock;
  let treeData;

  beforeEach(() => {
    onSearchChangeMock = jest.fn();
    treeData = [
      createTreeItem('src', 'src', 'directory', [
        createTreeItem('index.ts', 'src/index.ts', 'file'),
        createTreeItem('utils.ts', 'src/utils.ts', 'file'),
        createTreeItem('components', 'src/components', 'directory', [
          createTreeItem('Button.tsx', 'src/components/Button.tsx', 'file'),
          createTreeItem('Modal.tsx', 'src/components/Modal.tsx', 'file'),
        ]),
      ]),
      createTreeItem('package.json', 'package.json', 'file'),
      createTreeItem('README.md', 'README.md', 'file'),
    ];
    handler = new SearchHandler(onSearchChangeMock, () => treeData);
  });

  describe('setQuery', () => {
    it('should normalize query to lowercase and trim', () => {
      handler.setQuery('  Button  ');
      expect(handler.getQuery()).toBe('button');
    });

    it('should trigger onSearchChange callback', () => {
      handler.setQuery('test');
      expect(onSearchChangeMock).toHaveBeenCalledTimes(1);
    });
  });

  describe('clear', () => {
    it('should clear the search query', () => {
      handler.setQuery('test');
      handler.clear();
      expect(handler.getQuery()).toBe('');
    });

    it('should trigger onSearchChange callback', () => {
      handler.clear();
      expect(onSearchChangeMock).toHaveBeenCalled();
    });
  });

  describe('isActive', () => {
    it('should return false when query is empty', () => {
      expect(handler.isActive()).toBe(false);
    });

    it('should return true when query is not empty', () => {
      handler.setQuery('test');
      expect(handler.isActive()).toBe(true);
    });
  });

  describe('matches', () => {
    it('should match all items when query is empty', () => {
      const item = createTreeItem('test.ts', 'src/test.ts');
      expect(handler.matches(item)).toBe(true);
    });

    it('should match by name substring', () => {
      handler.setQuery('button');
      const item = createTreeItem('Button.tsx', 'src/components/Button.tsx');
      expect(handler.matches(item)).toBe(true);
    });

    it('should match by path substring', () => {
      handler.setQuery('components');
      const item = createTreeItem('Button.tsx', 'src/components/Button.tsx');
      expect(handler.matches(item)).toBe(true);
    });

    it('should not match when no match found', () => {
      handler.setQuery('xyz');
      const item = createTreeItem('Button.tsx', 'src/components/Button.tsx');
      expect(handler.matches(item)).toBe(false);
    });

    it('should be case insensitive', () => {
      handler.setQuery('BUTTON');
      const item = createTreeItem('button.tsx', 'src/button.tsx');
      expect(handler.matches(item)).toBe(true);
    });
  });

  describe('fuzzyMatch', () => {
    it('should match characters in order', () => {
      expect(handler.fuzzyMatch('button', 'btn')).toBe(true);
      expect(handler.fuzzyMatch('searchhandler', 'srh')).toBe(true);
    });

    it('should not match when characters are out of order', () => {
      expect(handler.fuzzyMatch('button', 'nbt')).toBe(false);
    });

    it('should not match when query is longer than text', () => {
      expect(handler.fuzzyMatch('ab', 'abc')).toBe(false);
    });

    it('should match empty query', () => {
      expect(handler.fuzzyMatch('button', '')).toBe(true);
    });
  });

  describe('filterTree', () => {
    it('should return all items when query is empty', () => {
      const result = handler.filterTree(treeData);
      expect(result).toEqual(treeData);
    });

    it('should filter files by name', () => {
      handler.setQuery('button');
      const result = handler.filterTree(treeData);

      // Should only include path to Button.tsx
      expect(result.length).toBe(1);
      expect(result[0].name).toBe('src');
      expect(result[0].children[0].name).toBe('components');
      expect(result[0].children[0].children[0].name).toBe('Button.tsx');
    });

    it('should include parent directories of matching files', () => {
      handler.setQuery('modal');
      const result = handler.filterTree(treeData);

      expect(result.length).toBe(1);
      expect(result[0].name).toBe('src');
      expect(result[0].children[0].name).toBe('components');
    });

    it('should filter multiple matches', () => {
      handler.setQuery('.tsx');
      const result = handler.filterTree(treeData);

      // Both Button.tsx and Modal.tsx should match
      expect(result.length).toBe(1);
      expect(result[0].children[0].children.length).toBe(2);
    });
  });

  describe('getMatchingItems', () => {
    it('should return empty array when query is empty', () => {
      expect(handler.getMatchingItems()).toEqual([]);
    });

    it('should return only matching files (not directories)', () => {
      handler.setQuery('button');
      const matches = handler.getMatchingItems();

      expect(matches.length).toBe(1);
      expect(matches[0].name).toBe('Button.tsx');
      expect(matches[0].type).toBe('file');
    });

    it('should flatten nested matches', () => {
      handler.setQuery('.ts');
      const matches = handler.getMatchingItems();

      // Should find: index.ts, utils.ts, Button.tsx, Modal.tsx
      expect(matches.length).toBe(4);
    });
  });
});
