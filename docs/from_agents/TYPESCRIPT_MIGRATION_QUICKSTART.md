# TypeScript Migration - Quick Start Guide

## 🎉 Great News: You're 95% Done!

### Current Build Setup

**Package.json scripts:**
```bash
npm run build              # Build global static/ts
npm run build:watch        # Watch mode for development
npm run build:writer       # Build writer app specifically
npm run type-check         # Type check without emitting
```

**TypeScript config (`tsconfig.json`):**
- Root compiles: `/static/ts/` → `/static/js/`
- Writer-specific: `/apps/writer_app/static/writer_app/ts/` → `/apps/writer_app/static/writer_app/js/`

### What's Left: ONE File! 🎯

**Only remaining JavaScript file:**
```
/apps/writer_app/static/writer_app/js/api-client.js (256 lines)
```

### Migration Steps (1 hour work!)

#### Step 1: Create TypeScript Version

```bash
cd /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts
```

Create `api-client.ts`:
```typescript
/**
 * WriterAPI - REST API client for scitex.writer.Writer
 */

interface SectionResponse {
    success: boolean;
    content?: string;
    error?: string;
}

interface WriteResponse {
    success: boolean;
    commit_hash?: string;
    error?: string;
}

interface HistoryResponse {
    success: boolean;
    commits?: Array<{
        hash: string;
        message: string;
        timestamp: string;
        author: string;
    }>;
    error?: string;
}

type DocumentType = 'manuscript' | 'supplementary' | 'revision';

export class WriterAPI {
    private projectId: string;
    private csrfToken: string;
    private baseUrl: string;

    constructor(projectId: string, csrfToken: string) {
        this.projectId = projectId;
        this.csrfToken = csrfToken;
        this.baseUrl = `/writer/api/project/${projectId}`;
    }

    async readSection(
        sectionName: string,
        docType: DocumentType = 'manuscript'
    ): Promise<string> {
        const url = `${this.baseUrl}/section/${sectionName}/?doc_type=${docType}`;
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            }
        });

        if (!response.ok) {
            throw new Error(`Failed to read section: ${response.status}`);
        }

        const data: SectionResponse = await response.json();
        if (!data.success || !data.content) {
            throw new Error(data.error || 'Failed to read section');
        }

        return data.content;
    }

    async writeSection(
        sectionName: string,
        content: string,
        docType: DocumentType = 'manuscript',
        commitMessage: string | null = null
    ): Promise<WriteResponse> {
        const url = `${this.baseUrl}/section/${sectionName}/`;
        const body: {
            content: string;
            doc_type: DocumentType;
            commit_message?: string;
        } = {
            content,
            doc_type: docType
        };

        if (commitMessage) {
            body.commit_message = commitMessage;
        }

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            throw new Error(`Failed to write section: ${response.status}`);
        }

        const data: WriteResponse = await response.json();
        if (!data.success) {
            throw new Error(data.error || 'Failed to write section');
        }

        return data;
    }

    async getSectionHistory(
        sectionName: string,
        docType: DocumentType = 'manuscript'
    ): Promise<HistoryResponse> {
        const url = `${this.baseUrl}/section/${sectionName}/history/?doc_type=${docType}`;
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            }
        });

        if (!response.ok) {
            throw new Error(`Failed to get history: ${response.status}`);
        }

        return await response.json();
    }

    // Add other methods from api-client.js here...
}

// Make available globally for templates that use <script> tags
if (typeof window !== 'undefined') {
    (window as any).WriterAPI = WriterAPI;
}
```

#### Step 2: Compile TypeScript

```bash
# From project root
npm run build:writer
```

This compiles `/apps/writer_app/static/writer_app/ts/**/*.ts` → `/js/**/*.js`

#### Step 3: Test

```bash
# Start dev server
./start_dev.sh

# Open browser console at http://127.0.0.1:8000/writer/
# Check if WriterAPI is available
console.log(typeof WriterAPI); // should output "function"
```

#### Step 4: Remove Old JavaScript (Optional)

Once confirmed working:
```bash
# Backup first
mv api-client.js api-client.js.backup

# The new compiled version from TS is already there!
```

### Build Commands Quick Reference

```bash
# Development - watch for changes
npm run build:watch

# Build writer app only
npm run build:writer

# Type check without building
npm run type-check

# Build everything
npm run build
```

### Verification Checklist

- [ ] Create `ts/api-client.ts` with types
- [ ] Run `npm run build:writer`
- [ ] Check `/js/api-client.js` was updated
- [ ] Check `/js/api-client.d.ts` exists
- [ ] Check `/js/api-client.js.map` exists
- [ ] Test in browser - API calls work
- [ ] Check DevTools - source maps work
- [ ] Test all writer pages

### Benefits of 100% TypeScript

✅ **Type Safety** - No more runtime type errors
✅ **Better IDE Support** - Full autocomplete everywhere
✅ **Unified Codebase** - All files follow same patterns
✅ **Source Maps** - Debug TypeScript directly in browser
✅ **Compile-time Checks** - Catch errors before deployment
✅ **Professional** - Modern, maintainable codebase

### After Migration

Your writer app will be **100% TypeScript**:
```
/ts/  (18 + 1 = 19 TypeScript files)
├── api-client.ts        ← NEW!
├── index.ts
├── helpers.ts
├── modules/ (11 files)
└── utils/ (5 files)

/js/  (Compiled output - 72+ files)
└── [All generated from TypeScript]
```

### Maintenance Notes

**DO:**
- ✅ Edit only `.ts` files in `/ts/` directory
- ✅ Run `npm run build:writer` after changes
- ✅ Commit `.ts` source files to Git
- ✅ Use `npm run build:watch` during development

**DON'T:**
- ❌ Edit `.js` files in `/js/` (they get overwritten!)
- ❌ Commit compiled `.js` files to Git (build artifacts)
- ❌ Manually write `.d.ts` files (auto-generated)

### .gitignore Recommendation

Add to `.gitignore`:
```gitignore
# TypeScript compiled output
apps/writer_app/static/writer_app/js/*.js
apps/writer_app/static/writer_app/js/*.js.map
apps/writer_app/static/writer_app/js/*.d.ts
apps/writer_app/static/writer_app/js/**/*.js
apps/writer_app/static/writer_app/js/**/*.js.map
apps/writer_app/static/writer_app/js/**/*.d.ts

# Keep old monolithic files directory
!apps/writer_app/static/writer_app/js/.old_monolithic_files/
```

**Reason:** Compiled files should be generated during deployment, not committed to Git.

### Deployment Note

Add to deployment script:
```bash
# Install dependencies
npm install

# Compile TypeScript
npm run build:writer

# Collect static files
python manage.py collectstatic --noinput
```

## Summary

🎯 **1 hour of work** → **100% TypeScript codebase**

The infrastructure is already in place, build scripts configured, 95% migrated. Just need to convert the last file and you're done! 🚀
