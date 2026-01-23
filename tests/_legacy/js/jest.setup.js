/**
 * Jest Setup File for SciTeX-Cloud Testing Environment
 * Global test configuration and utilities
 */

// Mock DOM APIs that might not be available in jsdom
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock fetch for API testing
global.fetch = jest.fn();

// Setup console methods for cleaner test output
const originalError = console.error;
beforeAll(() => {
  console.error = (...args) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOM.render is deprecated')
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

// Global test utilities
global.createMockElement = (tag, attributes = {}, textContent = '') => {
  const element = document.createElement(tag);
  Object.keys(attributes).forEach(key => {
    element.setAttribute(key, attributes[key]);
  });
  if (textContent) {
    element.textContent = textContent;
  }
  return element;
};