# SciTeX Frontend Testing Guide

## Overview

The SciTeX search integration is now complete with frontend JavaScript that provides a modern, progressive search experience.

## What Was Implemented

### 1. Frontend JavaScript Module

**File**: `/home/ywatanabe/proj/scitex-cloud/apps/scholar_app/static/scholar_app/scripts/scitex-search.js`

**Features**:
- ✅ Automatic SciTeX availability detection
- ✅ Progressive search with loading states
- ✅ Real-time engine status indicators
- ✅ Parallel/Single mode toggle
- ✅ Beautiful result cards with metadata
- ✅ Filter integration from existing form
- ✅ Error handling and user feedback

### 2. Integration Points

**Modified Files**:
- ✅ `index.html` - Added script include and URL configuration
- ✅ Existing search form - Works seamlessly (no changes needed)
- ✅ Existing filters - All filters work automatically

## How It Works

### User Flow

```
1. User enters query in search box
   ↓
2. User clicks "Search" button
   ↓
3. Form submission intercepted by scitex-search.js
   ↓
4. Loading state shown with engine status badges
   ↓
5. API call to /scholar/api/search/scitex/
   ↓
6. Results displayed in beautiful cards
   ↓
7. User can save papers, get citations, view PDFs
```

### Visual Features

**Loading State**:
- Animated progress bar
- Engine status badges showing which engines are searching
- Spinner animations

**Results Display**:
- Clean, modern cards for each paper
- Color-coded engine badges showing which engines found the paper
- Open Access, citation count, and DOI badges
- Action buttons: PDF, View Online, Save, Cite

**Search Mode Toggle**:
- Button next to search: "Parallel" or "Single"
- Click to toggle between modes
- Parallel = Fast (default)
- Single = Safe for rate limits

## Testing Instructions

### 1. Start the Server

```bash
cd /home/ywatanabe/proj/scitex-cloud

# Load development environment
source deployment/dotenvs/dotenv_dev

# Start Django
./deployment/server/server.sh
```

### 2. Open Browser

Navigate to: `http://127.0.0.1:8000/scholar/`

### 3. Test Basic Search

**Test Query #1: Famous Paper**
```
Query: "Attention is All You Need"
Expected: Should find the Transformer paper (2017)
         Authors: Vaswani, et al.
         DOI: 10.48550/arXiv.1706.03762
```

**Test Query #2: Recent Research**
```
Query: "deep learning"
Filters: Year from: 2023
Expected: Recent papers on deep learning
         Multiple results with 2023 publication dates
```

**Test Query #3: Open Access**
```
Query: "machine learning"
Filters: ✓ Open Access Only
Expected: Only papers with Open Access badge
```

### 4. Test Advanced Features

#### Test Parallel vs Single Mode

1. Click the **"Parallel"** button next to search
2. Button changes to **"Single"**
3. Run the same search
4. Single mode should be slightly slower but more reliable

#### Test Engine Status

1. Enter any query
2. Watch the loading state
3. You should see badges for engines like:
   - 🗄️ CrossRef (blue)
   - ❤️ PubMed (red)
   - 📄 arXiv (orange)
   - 🧠 Semantic Scholar (purple)
   - 📖 OpenAlex (teal)

4. After search, successful engines show colored badges on results

#### Test Filter Integration

1. Expand "Advanced Filters"
2. Set filters:
   - Year from: 2020
   - Year to: 2024
   - Author: "Smith"
   - Minimum Citations: 100+
3. Click Search
4. All filters should be applied to results

### 5. Browser Console Checks

Open browser console (F12) and look for:

```
[SciTeX Search] Initializing...
[SciTeX Search] Available and ready
[SciTeX Search] Available engines: Array(5)
[SciTeX Search] Event listeners attached
```

When searching:
```
[SciTeX Search] Searching: http://127.0.0.1:8000/scholar/api/search/scitex/?q=...
[SciTeX Search] Found 5 results in 2.30s
```

## Example Test Queries

### Computer Science

| Query | Expected Results |
|-------|------------------|
| `"BERT transformer"` | NLP papers, recent |
| `"GPT-3"` | OpenAI papers, high citations |
| `"neural architecture search"` | AutoML papers |

### Neuroscience

| Query | Filters | Expected |
|-------|---------|----------|
| `"visual cortex"` | PubMed source | Biomedical papers |
| `"fMRI brain"` | Year: 2020-2024 | Recent neuroimaging |
| `"neural mechanisms"` | Open Access ✓ | Free access papers |

### General Science

| Query | Expected |
|-------|----------|
| `"climate change"` | Diverse sources |
| `"CRISPR gene editing"` | High citation counts |
| `"quantum computing"` | Mix of preprints and articles |

## Troubleshooting

### Issue: Search button does nothing

**Check**:
1. Open console (F12)
2. Look for JavaScript errors
3. Check if scitex-search.js loaded: `console.log(typeof ScitexSearch)`
4. Should output: `"object"`

**Fix**:
- Hard refresh: Ctrl+Shift+R (clear cache)
- Check file exists: `/scholar_app/static/scholar_app/scripts/scitex-search.js`

### Issue: "SciTeX not available" in console

**Check**:
1. Is SciTeX package installed?
   ```bash
   python -c "from scitex.scholar.metadata_engines import ScholarPipelineSearchParallel; print('OK')"
   ```

2. Check API endpoint:
   ```bash
   curl http://127.0.0.1:8000/scholar/api/search/scitex/capabilities/
   ```

**Fix**:
- See `SCITEX_SEARCH_INTEGRATION.md` troubleshooting section
- Restart Django server
- Check settings.py for SCITEX_* variables

### Issue: Results don't show

**Check**:
1. Console for errors
2. Network tab (F12) - look for 200 status on `/api/search/scitex/`
3. Response has `results` array

**Fix**:
- Check backend logs
- Verify API returns data: `curl "http://127.0.0.1:8000/scholar/api/search/scitex/?q=test"`

### Issue: Slow searches

**Solutions**:
1. Switch to Single mode (reduces parallel overhead)
2. Use fewer engines in dotenv_dev:
   ```bash
   export SCITEX_SCHOLAR_ENGINES="CrossRef,PubMed"
   ```
3. Enable caching:
   ```bash
   export SCITEX_SCHOLAR_USE_CACHE=True
   ```

## Visual Indicators

### Search Modes

**Parallel Mode** (default):
```
[🗲 Parallel]  ← Button shows lightning bolt
Fast search, uses all engines simultaneously
```

**Single Mode**:
```
[🛡️ Single]  ← Button shows shield
Safer search, engines queried sequentially
```

### Engine Status

**During Search** (loading):
```
[🗄️ CrossRef ⏳] [❤️ PubMed ⏳] [📄 arXiv ⏳]
```

**After Search** (success):
```
[🗄️ CrossRef] [❤️ PubMed] [📄 arXiv]
(colored badges on results)
```

### Result Badges

- 🔓 **Open Access** (green) - Free to read
- 💬 **150 citations** (blue) - Citation count
- 📝 **DOI: 10.xxx** (gray) - Digital Object Identifier
- **Engine badges** (colored) - Which engines found it

## Performance Expectations

### Response Times

| Scenario | Expected Time |
|----------|--------------|
| First search (no cache) | 2-5 seconds |
| Cached search | < 0.5 seconds |
| Parallel mode (5 engines) | 2-3 seconds |
| Single mode (5 engines) | 4-6 seconds |

### Result Counts

| Query Type | Typical Results |
|------------|----------------|
| Specific paper title | 1-5 results |
| General topic | 10-100 results |
| Broad keyword | 100+ results |

## Advanced Usage

### Programmatic Access

You can also use the search programmatically:

```javascript
// In browser console
const results = await ScitexSearch.executeSearch(
    "machine learning",
    {
        year_start: 2020,
        open_access: true,
        max_results: 20
    }
);

console.log(results);
```

### Inspect Search State

```javascript
// Check current state
console.log(ScitexSearch.state);

// Output:
// {
//   isSearching: false,
//   currentQuery: "machine learning",
//   lastResults: {...},
//   engines: ["CrossRef", "PubMed", ...],
//   searchMode: "parallel"
// }
```

### Custom Engine Selection

Modify source checkboxes behavior to work with SciTeX (future enhancement).

## Next Steps

After testing works:

1. **Integrate Save functionality**
   - Connect to existing UserLibrary model
   - Add collections dropdown

2. **Integrate Citation export**
   - Connect to existing BibTeX export
   - Add format selection (BibTeX, RIS, etc.)

3. **Add search history**
   - Show recent searches
   - Save searches for alerts

4. **Performance optimization**
   - Add request debouncing
   - Implement infinite scroll
   - Add result caching in frontend

## Success Criteria

✅ Search form works without errors
✅ Loading state shows during search
✅ Results display in cards
✅ Engine badges show which sources found each paper
✅ Mode toggle works (Parallel ↔ Single)
✅ Filters apply correctly
✅ PDF/external links open
✅ Console shows successful search logs

## Demo Video Script

If creating a demo:

1. **Show search box**: "This is the SciTeX-powered search"
2. **Enter query**: "Attention is All You Need"
3. **Point to loading**: "Watch the engines searching in parallel"
4. **Show result**: "Found the famous Transformer paper"
5. **Point to badges**: "CrossRef, arXiv, and Semantic Scholar all found it"
6. **Toggle mode**: "I can switch to single mode for rate limit safety"
7. **Test filter**: "Let me filter for only Open Access papers from 2023"
8. **Show results**: "All results match my filters"

---

**Last Updated**: 2025-10-22
**Version**: 1.0.0
**Status**: Ready for Testing 🎉
