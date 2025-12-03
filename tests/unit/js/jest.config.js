/**
 * Jest Configuration for SciTeX-Cloud JavaScript/TypeScript Unit Tests
 * Located in tests/unit/js/ for tree component testing
 */

module.exports = {
  testEnvironment: 'jsdom',

  testMatch: [
    '**/*.test.js',
    '**/*.test.ts',
  ],

  rootDir: '.',

  // Coverage configuration
  collectCoverage: false,
  coverageDirectory: '../../../coverage/js',
  coverageReporters: ['text', 'lcov'],

  // Clear mocks between tests
  clearMocks: true,

  // Verbose output for debugging
  verbose: true,

  // Transform for TypeScript (if needed later)
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': 'babel-jest',
  },

  // Module resolution
  moduleFileExtensions: ['js', 'ts', 'json'],
};
