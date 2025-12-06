# Queue Management Integration Guide

This guide explains how to integrate the modular queue management JavaScript and CSS into the Scholar app's HTML templates.

## Quick Start

### Step 1: Add Static File Imports

In `apps/scholar_app/templates/scholar_app/index.html` or any template using queue management:

```html
{% load static %}

<!-- In the <head> section -->
<link rel="stylesheet" href="{% static 'scholar_app/css/queue-management.css' %}">

<!-- Before closing </body> tag -->
<script type="module">
    import { initQueueManagement } from '{% static "scholar_app/js/queue-management.js" %}';

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', () => {
        initQueueManagement({
            resourceStatusUrl: '{% url "scholar_app:bibtex_resource_status" %}',
            pollInterval: 2000  // Poll every 2 seconds
        });
    });

    // Clean up on page unload
    window.addEventListener('beforeunload', () => {
        import('{% static "scholar_app/js/queue-management.js" %}')
            .then(module => module.stopQueueManagement());
    });
</script>
```

## Replacing Inline Code

### Current Structure (index.html)

Currently, the index.html file has ~2978 lines including:
- Inline JavaScript (lines ~2615-2800+)
- Inline CSS styles (scattered throughout)

### Target Structure

After refactoring, the structure should be:

```html
{% extends "scholar_app/scholar_base.html" %}
{% load static %}
{% load custom_filters %}

{% block extra_css %}
<!-- Load queue management styles -->
<link rel="stylesheet" href="{% static 'scholar_app/css/queue-management.css' %}">
{% endblock %}

{% block content %}
<!-- HTML content with semantic classes -->
<div class="scitex-resource-monitor">
    <!-- Resource cards using CSS classes -->
</div>

<div id="activeJobsList" class="scitex-jobs-list">
    <div class="scitex-jobs-list-header">
        <i class="fas fa-cog fa-spin"></i> Active Jobs
    </div>
    <div id="activeJobsContent" class="scitex-jobs-list-content">
        <!-- Populated by JavaScript -->
    </div>
</div>

<div id="queuedJobsList" class="scitex-jobs-list">
    <div class="scitex-jobs-list-header">
        <i class="fas fa-hourglass-half"></i> Queued Jobs
    </div>
    <div id="queuedJobsContent" class="scitex-jobs-list-content">
        <!-- Populated by JavaScript -->
    </div>
</div>
{% endblock %}

{% block extra_js %}
<!-- Load queue management JavaScript -->
<script type="module">
    import { initQueueManagement } from '{% static "scholar_app/js/queue-management.js" %}';

    document.addEventListener('DOMContentLoaded', () => {
        initQueueManagement({
            resourceStatusUrl: '{% url "scholar_app:bibtex_resource_status" %}',
            pollInterval: 2000
        });
    });
</script>
{% endblock %}
```

## Step-by-Step Migration

### 1. Replace Inline Styles with CSS Classes

**Before (inline styles):**
```html
<div style="background: var(--color-canvas-default); padding: 0.75rem; border-radius: 6px;">
    <!-- content -->
</div>
```

**After (CSS classes):**
```html
<div class="scitex-resource-card">
    <!-- content -->
</div>
```

### 2. Remove Inline JavaScript

**Before (in index.html lines 2615-2800):**
```html
<script>
    let resourceMonitorInterval = null;

    function updateResourceMonitor() {
        fetch("{% url 'scholar_app:bibtex_resource_status' %}")
            .then(response => response.json())
            .then(data => {
                // ... lots of code ...
            });
    }

    function cancelJob(jobId) {
        // ... more code ...
    }

    // Start polling
    updateResourceMonitor();
    resourceMonitorInterval = setInterval(updateResourceMonitor, 2000);
</script>
```

**After (import module):**
```html
<script type="module">
    import { initQueueManagement } from '{% static "scholar_app/js/queue-management.js" %}';

    document.addEventListener('DOMContentLoaded', () => {
        initQueueManagement({
            resourceStatusUrl: '{% url "scholar_app:bibtex_resource_status" %}',
            pollInterval: 2000
        });
    });
</script>
```

### 3. Update HTML Structure

Replace inline-styled divs with semantic classes:

**Resource Cards:**
```html
<!-- Before -->
<div style="background: var(--color-canvas-default); padding: 0.75rem; border-radius: 6px; border: 1px solid var(--color-border-default);">
    <div style="color: var(--color-fg-muted); font-size: 0.85rem; margin-bottom: 0.25rem;">CPU Usage</div>
    <div style="color: var(--scitex-color-03); font-size: 1.5rem; font-weight: 700;">
        <span id="cpuPercent">0</span>%
    </div>
</div>

<!-- After -->
<div class="scitex-resource-card">
    <div class="scitex-resource-card-label">CPU Usage</div>
    <div class="scitex-resource-card-value scitex-resource-card-value--cpu">
        <span id="cpuPercent">0</span>%
    </div>
</div>
```

**Job Cards:**
The JavaScript module already generates these with proper classes, so no HTML changes needed - just ensure the container divs exist:

```html
<div id="activeJobsList" class="scitex-jobs-list" style="display: none;">
    <div class="scitex-jobs-list-header">
        <i class="fas fa-cog fa-spin"></i> Active Jobs
    </div>
    <div id="activeJobsContent" class="scitex-jobs-list-content">
        <!-- JavaScript will populate this -->
    </div>
</div>
```

## Configuration Options

### JavaScript Configuration

```javascript
initQueueManagement({
    // Required: URL for resource status endpoint
    resourceStatusUrl: '/scholar/api/bibtex/resource-status/',

    // Optional: Polling interval in milliseconds (default: 2000)
    pollInterval: 2000,

    // Optional: Custom callback for job updates
    onJobUpdate: (jobs) => {
        console.log('Jobs updated:', jobs);
    },

    // Optional: Custom error handler
    onError: (error) => {
        console.error('Queue error:', error);
    }
});
```

### CSS Customization

Override CSS variables in your theme:

```css
:root {
    --scitex-queue-position-1-color: #28a745;  /* Green */
    --scitex-queue-position-2-color: #007bff;  /* Blue */
    --scitex-queue-position-3-color: #ffc107;  /* Orange */
}
```

## File Structure

After integration, your file structure should look like:

```
apps/scholar_app/
├── static/
│   └── scholar_app/
│       ├── css/
│       │   ├── queue-management.css      # Queue styles
│       │   └── scholar.css               # Other scholar styles
│       └── js/
│           ├── queue-management.js       # Queue functionality
│           └── scholar.js                # Other scholar scripts
├── templates/
│   └── scholar_app/
│       ├── index.html                    # Main page (refactored)
│       ├── scholar_base.html             # Base template
│       └── ...
└── ...
```

## Testing After Integration

### 1. Check Static Files Load

Open browser DevTools → Network tab:
- ✅ `queue-management.css` loads (200 OK)
- ✅ `queue-management.js` loads (200 OK)

### 2. Check Console for Errors

Open browser DevTools → Console tab:
- ✅ No import errors
- ✅ No reference errors
- ✅ `initQueueManagement` called successfully

### 3. Verify Functionality

- ✅ Resource stats update every 2 seconds
- ✅ Active jobs display correctly
- ✅ Queued jobs show position indicators
- ✅ Cancel button works
- ✅ Privacy messages appear for other users' jobs

### 4. Test Visual Appearance

- ✅ Cards styled correctly
- ✅ Colors match design system
- ✅ Responsive on mobile
- ✅ Dark mode works

## Troubleshooting

### Issue: "Failed to load module"

**Cause:** Incorrect static file path
**Solution:** Check that `{% static %}` tag is used correctly:

```html
<!-- Wrong -->
<script src="/static/scholar_app/js/queue-management.js"></script>

<!-- Right -->
<script type="module" src="{% static 'scholar_app/js/queue-management.js' %}"></script>
```

### Issue: "Cannot read property 'textContent' of null"

**Cause:** JavaScript trying to access elements before DOM loads
**Solution:** Wrap in `DOMContentLoaded`:

```javascript
document.addEventListener('DOMContentLoaded', () => {
    initQueueManagement({ ... });
});
```

### Issue: Styles not applying

**Cause:** CSS file not loaded or specificity issues
**Solution:**
1. Verify CSS file loads in Network tab
2. Check browser DevTools → Elements tab → Computed styles
3. Ensure CSS link is in `<head>` section

### Issue: CSRF token errors

**Cause:** Token not found in page
**Solution:** Ensure CSRF token exists:

```html
{% csrf_token %}
```

### Issue: Polling stops after navigation

**Cause:** Event listeners not cleaned up
**Solution:** Add cleanup:

```javascript
window.addEventListener('beforeunload', () => {
    stopQueueManagement();
});
```

## Performance Optimization

### 1. Lazy Loading

Load queue management only when needed:

```javascript
// Only load on pages with upload form
const uploadForm = document.getElementById('bibtexEnrichmentForm');
if (uploadForm) {
    import('{% static "scholar_app/js/queue-management.js" %}')
        .then(module => {
            module.initQueueManagement({ ... });
        });
}
```

### 2. Debounced Updates

Reduce update frequency:

```javascript
let updateTimeout;
function debouncedUpdate() {
    clearTimeout(updateTimeout);
    updateTimeout = setTimeout(() => {
        updateResourceMonitor();
    }, 100);
}
```

### 3. Conditional Polling

Stop polling when tab is hidden:

```javascript
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        stopQueueManagement();
    } else {
        initQueueManagement({ ... });
    }
});
```

## Next Steps

1. **Backup current index.html:**
   ```bash
   cp apps/scholar_app/templates/scholar_app/index.html \
      apps/scholar_app/templates/scholar_app/index.html.backup
   ```

2. **Replace inline code** section by section:
   - First: CSS (low risk)
   - Second: JavaScript (test thoroughly)

3. **Test each change** before proceeding to next

4. **Deploy to staging** before production

5. **Monitor for errors** in production logs

## Rollback Plan

If issues occur after deployment:

```bash
# Restore backup
cp apps/scholar_app/templates/scholar_app/index.html.backup \
   apps/scholar_app/templates/scholar_app/index.html

# Restart server
sudo systemctl restart gunicorn
```

## Support

For questions or issues:
- Check documentation: `docs/QUEUE_MANAGEMENT_IMPLEMENTATION.md`
- Review code comments in JavaScript module
- Contact: Claude Code implementation team

---

**Last Updated:** 2025-10-22
**Version:** 1.0
**Status:** Ready for Integration
