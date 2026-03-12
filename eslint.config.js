// ESLint v9+ Flat Config (SAFE MODE - Read-only by default)
// See: https://eslint.org/docs/latest/use/configure/configuration-files-new
//
// IMPORTANT: This config ONLY detects inline styles (no auto-fix by default)
// Run with: eslint "apps/**/*.{ts,js}"  (READ-ONLY - safe)
// Run with: eslint --fix "apps/**/*.{ts,js}"  (DESTRUCTIVE - be careful!)

import tsParser from '@typescript-eslint/parser';
import tsPlugin from '@typescript-eslint/eslint-plugin';

export default [
  {
    // Global ignores (applies to all configs)
    ignores: [
      '**/node_modules/**',
      '**/dist/**',
      '**/build/**',
      '**/*.min.js',
      '**/externals/**',
      '**/vendor/**',
      '**/staticfiles/**',
      '**/media/**',
      '**/migrations/**',
      '**/.venv/**',
      '**/data/**',
      '**/logs/**',
      '**/.tsbuild/**',
    ],
  },
  {
    // TypeScript files configuration
    files: ['**/*.ts', '**/*.tsx'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: 'module',
      },
      globals: {
        // Browser globals
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        fetch: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
        alert: 'readonly',
        confirm: 'readonly',
        prompt: 'readonly',
        // Node globals
        process: 'readonly',
        __dirname: 'readonly',
        __filename: 'readonly',
        module: 'readonly',
        require: 'readonly',
        exports: 'readonly',
        global: 'readonly',
        // Common libraries (declared globally in templates)
        monaco: 'readonly',
        CodeMirror: 'readonly',
        bootstrap: 'readonly',
        fabric: 'readonly',
      },
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
    },
    rules: {
      // TypeScript rules
      '@typescript-eslint/no-unused-vars': [
        'warn',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
        },
      ],
      '@typescript-eslint/no-explicit-any': 'warn',

      // ⚠️ CRITICAL: NO INLINE STYLES RULE (ERROR - blocks violations)
      'no-restricted-syntax': [
        'error',
        {
          selector: 'Literal[value=/style\\s*=/]',
          message: '❌ INLINE STYLES FORBIDDEN: Use CSS classes instead. See GITIGNORED/RULES/00_DJANGO_ORGANIZATION_FULLSTACK.md:34. For dynamic styles, use <style> tags with generated CSS rules (see apps/figrecipe_app/static/figrecipe_app/ts/vis/DataTableManager.ts:424-436 for pattern).',
        },
        {
          selector: 'TemplateLiteral[quasis.*.value.raw=/style\\s*=/]',
          message: '❌ INLINE STYLES FORBIDDEN: Use CSS classes instead. See GITIGNORED/RULES/00_DJANGO_ORGANIZATION_FULLSTACK.md:34. For dynamic styles, use <style> tags with generated CSS rules (see apps/figrecipe_app/static/figrecipe_app/ts/vis/DataTableManager.ts:424-436 for pattern).',
        },
      ],
    },
  },
  {
    // JavaScript files configuration
    files: ['**/*.js', '**/*.mjs'],
    languageOptions: {
      ecmaVersion: 2020,
      sourceType: 'module',
      globals: {
        // Browser globals
        window: 'readonly',
        document: 'readonly',
        console: 'readonly',
        fetch: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
        alert: 'readonly',
        confirm: 'readonly',
        prompt: 'readonly',
        // Node globals
        process: 'readonly',
        __dirname: 'readonly',
        __filename: 'readonly',
        module: 'readonly',
        require: 'readonly',
        exports: 'readonly',
        global: 'readonly',
        // Common libraries (declared globally in templates)
        monaco: 'readonly',
        CodeMirror: 'readonly',
        bootstrap: 'readonly',
        fabric: 'readonly',
      },
    },
    rules: {
      // ⚠️ CRITICAL: NO INLINE STYLES RULE (ERROR - blocks violations)
      // This rule detects 'style="..."' in string literals and template literals
      'no-restricted-syntax': [
        'error',
        {
          // Detect style=" in string literals
          selector: 'Literal[value=/style\\s*=/]',
          message: '❌ INLINE STYLES FORBIDDEN: Use CSS classes instead. See GITIGNORED/RULES/00_DJANGO_ORGANIZATION_FULLSTACK.md:34. For dynamic styles, use <style> tags with generated CSS rules (see apps/figrecipe_app/static/figrecipe_app/ts/vis/DataTableManager.ts:424-436 for pattern).',
        },
        {
          // Detect style=" in template literals
          selector: 'TemplateLiteral[quasis.*.value.raw=/style\\s*=/]',
          message: '❌ INLINE STYLES FORBIDDEN: Use CSS classes instead. See GITIGNORED/RULES/00_DJANGO_ORGANIZATION_FULLSTACK.md:34. For dynamic styles, use <style> tags with generated CSS rules (see apps/figrecipe_app/static/figrecipe_app/ts/vis/DataTableManager.ts:424-436 for pattern).',
        },
      ],
    },
  },
];
