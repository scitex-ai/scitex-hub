# Security Features Implementation Documentation

## Overview

This document describes the implementation of GitHub-style security features for SciTeX projects. The security system provides comprehensive vulnerability scanning, dependency management, security policy enforcement, and advisory publication capabilities.

**Implementation Date:** 2025-10-24
**Version:** 1.0
**Status:** Complete

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Database Models](#database-models)
3. [Security Scanning Service](#security-scanning-service)
4. [Views and Templates](#views-and-templates)
5. [URL Patterns](#url-patterns)
6. [API Endpoints](#api-endpoints)
7. [Usage Guide](#usage-guide)
8. [Integration](#integration)
9. [Future Enhancements](#future-enhancements)

---

## Architecture Overview

### Design Philosophy

The security system follows GitHub's security model with these key principles:

- **Proactive Security**: Automated scanning detects vulnerabilities before they become issues
- **Transparency**: All security alerts are visible to project collaborators
- **Actionable**: Each alert provides clear remediation steps
- **Non-intrusive**: Security features integrate seamlessly without disrupting workflows

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Dashboard                        │
│  (Overview, Alerts, Policy, Advisories, Dependencies)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Security Views Layer                      │
│  • security_overview()     • security_alerts()              │
│  • security_alert_detail() • security_policy_edit()         │
│  • security_advisories()   • dependency_graph()             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Security Scanning Service                   │
│  • Dependency Vulnerability Scanning (pip-audit, safety)    │
│  • Secret Detection (detect-secrets)                        │
│  • Static Code Analysis (bandit)                            │
│  • Outdated Dependency Detection                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Database Models                         │
│  • SecurityAlert      • SecurityPolicy                       │
│  • SecurityAdvisory   • DependencyGraph                      │
│  • SecurityScanResult                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Models

### Location
`/home/ywatanabe/proj/scitex-cloud/apps/project_app/models/security.py`

### Models

#### 1. SecurityAlert

Tracks security vulnerabilities and issues detected in the project.

**Fields:**
- `project` - ForeignKey to Project
- `alert_type` - Type of alert (dependency, secret, code, outdated)
- `severity` - Severity level (critical, high, medium, low, info)
- `status` - Current status (open, dismissed, fixed, wont_fix)
- `title` - Short description
- `description` - Detailed explanation
- `affected_package` - Package name (for dependency alerts)
- `affected_version` - Current version
- `fixed_version` - Version with fix
- `cve_id` - CVE identifier
- `advisory_url` - Link to security advisory
- `file_path` - File location (for code/secret alerts)
- `line_number` - Line number
- `fix_available` - Whether automatic fix exists
- `fix_pr_url` - Link to fix PR
- `dismissed_at` - Dismissal timestamp
- `dismissed_by` - User who dismissed
- `dismissed_reason` - Dismissal reason

**Key Methods:**
- `dismiss(user, reason)` - Dismiss the alert
- `mark_fixed()` - Mark as fixed
- `is_open()` - Check if still open
- `get_severity_badge_class()` - Get Bootstrap class for severity

**Example Usage:**
```python
from apps.project_app.models.security import SecurityAlert

# Create alert
alert = SecurityAlert.objects.create(
    project=project,
    alert_type='dependency',
    severity='high',
    title='Vulnerable dependency: requests',
    description='CVE-2024-1234 affects requests < 2.32.0',
    affected_package='requests',
    affected_version='2.28.0',
    fixed_version='2.32.0',
    cve_id='CVE-2024-1234',
    fix_available=True
)

# Dismiss alert
alert.dismiss(user=request.user, reason='False positive')
```

#### 2. SecurityPolicy

Manages the project's security policy (SECURITY.md file).

**Fields:**
- `project` - OneToOneField to Project
- `content` - Markdown content
- `contact_email` - Security contact email
- `contact_url` - Security reporting URL
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp
- `created_by` - User who created policy

**Key Methods:**
- `save_to_file()` - Save policy to SECURITY.md
- `load_from_file(project)` - Load policy from SECURITY.md

**Example Usage:**
```python
from apps.project_app.models.security import SecurityPolicy

# Create/update policy
policy, created = SecurityPolicy.objects.get_or_create(
    project=project,
    defaults={
        'content': '# Security Policy\n\n...',
        'contact_email': 'security@example.com',
        'created_by': request.user
    }
)

# Save to file
policy.save_to_file()
```

#### 3. SecurityAdvisory

Published security advisories for the project.

**Fields:**
- `project` - ForeignKey to Project
- `status` - Publication status (draft, published, closed)
- `severity` - Severity level
- `title` - Advisory title
- `description` - Detailed description
- `mitigation` - Mitigation steps
- `cve_id` - CVE identifier (unique)
- `cwe_id` - CWE identifier
- `affected_versions` - Version range affected
- `patched_versions` - Patched versions
- `reported_by` - Reporter name
- `published_at` - Publication timestamp
- `created_by` - User who created advisory

**Key Methods:**
- `publish()` - Publish the advisory
- `is_published()` - Check if published

#### 4. DependencyGraph

Tracks project dependencies for vulnerability scanning.

**Fields:**
- `project` - ForeignKey to Project
- `package_name` - Package name
- `version` - Package version
- `package_type` - Type (python, npm, etc.)
- `dependencies_json` - JSON array of dependencies
- `is_direct` - Direct dependency flag
- `is_dev_dependency` - Development dependency flag
- `has_vulnerabilities` - Vulnerability flag
- `vulnerability_count` - Number of vulnerabilities
- `last_scanned` - Last scan timestamp

**Properties:**
- `dependencies` - Python list of dependencies

**Key Methods:**
- `get_dependency_tree(depth=0, max_depth=3)` - Build dependency tree

#### 5. SecurityScanResult

Records history of security scans.

**Fields:**
- `project` - ForeignKey to Project
- `scan_type` - Type of scan (dependency, secret, code, full)
- `status` - Scan status (pending, running, completed, failed)
- `alerts_created` - Number of new alerts
- `critical_count` - Critical alerts count
- `high_count` - High severity count
- `medium_count` - Medium severity count
- `low_count` - Low severity count
- `scan_duration` - Duration in seconds
- `error_message` - Error message if failed
- `started_at` - Start timestamp
- `completed_at` - Completion timestamp
- `triggered_by` - User who triggered scan

**Key Methods:**
- `complete(duration)` - Mark scan as completed
- `fail(error_message)` - Mark scan as failed

---

## Security Scanning Service

### Location
`/home/ywatanabe/proj/scitex-cloud/apps/project_app/services/security_scanning.py`

### SecurityScanner Class

Main orchestrator for security scanning operations.

#### Key Methods

##### `run_full_scan(user=None) -> Dict`

Runs a complete security scan including:
1. Dependency vulnerability scanning
2. Secret detection
3. Code analysis
4. Outdated dependency checks

**Returns:**
```python
{
    'alerts': [...],           # List of alert dictionaries
    'critical': 0,             # Count of critical issues
    'high': 0,                 # Count of high severity issues
    'medium': 0,               # Count of medium severity issues
    'low': 0,                  # Count of low severity issues
    'errors': [],              # List of error messages
    'scan_id': 123,            # Scan result ID
    'duration': 12.5           # Scan duration in seconds
}
```

**Example:**
```python
from apps.project_app.services.security_scanning import SecurityScanner

scanner = SecurityScanner(project)
results = scanner.run_full_scan(user=request.user)

if results['critical'] > 0:
    # Alert project maintainers
    notify_maintainers(project, results)
```

##### `scan_dependencies() -> Dict`

Scans Python dependencies using pip-audit or safety.

**Supported Tools:**
- **pip-audit** (preferred): Modern, maintained, supports JSON output
- **safety**: Legacy fallback, uses safety-db

**Requirements File Detection:**
- `requirements.txt`
- `pyproject.toml`

##### `scan_secrets() -> Dict`

Scans for hardcoded secrets using detect-secrets.

**Detects:**
- API keys
- Passwords
- Tokens
- Private keys
- Database credentials

##### `scan_code() -> Dict`

Static code analysis using bandit for Python security issues.

**Checks for:**
- SQL injection vulnerabilities
- XSS vulnerabilities
- Insecure cryptography
- Shell injection
- Weak random number generation

##### `check_outdated_dependencies() -> Dict`

Checks for outdated dependencies using pip list.

### CVELookup Class

Utility class for looking up CVE information.

#### Methods

##### `lookup_cve(cve_id: str) -> Optional[Dict]`

Looks up CVE information from NVD database.

**Example:**
```python
from apps.project_app.services.security_scanning import CVELookup

cve_info = CVELookup.lookup_cve('CVE-2024-1234')
if cve_info:
    print(f"Severity: {cve_info['severity']}")
    print(f"Description: {cve_info['description']}")
```

---

## Views and Templates

### Location
- Views: `/home/ywatanabe/proj/scitex-cloud/apps/project_app/views/security_views.py`
- Templates: `/home/ywatanabe/proj/scitex-cloud/apps/project_app/templates/project_app/security/`

### Views

#### 1. security_overview(request, username, slug)

Security dashboard showing:
- Open alerts summary by severity
- Closed alerts count
- Dependency statistics
- Recent open alerts
- Recent security scans
- Security policy status

**Template:** `security_overview.html`

**Features:**
- Real-time statistics
- One-click security scan trigger
- Navigation to all security sections

#### 2. security_alerts(request, username, slug)

List view of all security alerts with filtering.

**Filters:**
- Status (open, fixed, dismissed)
- Severity (critical, high, medium, low)
- Type (dependency, secret, code, outdated)

**Template:** `security_alerts.html`

**Features:**
- Pagination (25 per page)
- Severity badges
- Quick alert preview
- Time since creation

#### 3. security_alert_detail(request, username, slug, alert_id)

Detailed view of a single security alert.

**Template:** `security_alert_detail.html`

**Features:**
- Full alert description
- CVE links
- File location (if applicable)
- Dismiss functionality
- Reopen capability
- Create fix PR (placeholder)

#### 4. security_policy_edit(request, username, slug)

Edit security policy (SECURITY.md).

**Template:** `security_policy.html`

**Features:**
- Markdown editor
- Contact information fields
- Auto-save to SECURITY.md
- Read-only view for non-editors

#### 5. security_advisories(request, username, slug)

List published security advisories.

**Template:** `security_advisories.html`

**Features:**
- Published advisories only
- Severity badges
- CVE identifiers
- Affected/patched versions

#### 6. dependency_graph(request, username, slug)

Visualize project dependencies.

**Template:** `dependency_graph.html`

**Features:**
- Dependency statistics
- Direct dependencies list
- Vulnerability indicators
- Last scan timestamp

#### 7. scan_history(request, username, slug)

Historical record of security scans.

**Template:** `scan_history.html`

**Features:**
- Scan type and status
- Alert counts by severity
- Scan duration
- Triggered by user

### Templates

All templates follow GitHub's design patterns with:
- Clean, minimalist interface
- Severity color coding (critical: red, high: red, medium: yellow, low: blue)
- Octicons for visual consistency
- Responsive design
- Accessibility features

**Color Scheme:**
```css
Critical: #d1242f (bright red)
High:     #cf222e (red)
Medium:   #bf8700 (yellow/orange)
Low:      #1168c4 (blue)
Info:     #656d76 (gray)
```

---

## URL Patterns

### Location
`/home/ywatanabe/proj/scitex-cloud/apps/project_app/user_urls.py`

### Security URLs

All security URLs follow GitHub's pattern: `/<username>/<slug>/security/`

```python
# Main security views
path('<slug:slug>/security/', security_views.security_overview, name='security_overview')
path('<slug:slug>/security/alerts/', security_views.security_alerts, name='security_alerts')
path('<slug:slug>/security/alerts/<int:alert_id>/', security_views.security_alert_detail, name='security_alert_detail')
path('<slug:slug>/security/policy/', security_views.security_policy_edit, name='security_policy')
path('<slug:slug>/security/advisories/', security_views.security_advisories, name='security_advisories')
path('<slug:slug>/security/dependabot/', security_views.dependency_graph, name='dependency_graph')
path('<slug:slug>/security/scans/', security_views.scan_history, name='scan_history')

# API endpoints
path('<slug:slug>/api/security/scan/', security_views.trigger_security_scan, name='api_trigger_scan')
path('<slug:slug>/api/security/alerts/<int:alert_id>/dismiss/', security_views.dismiss_alert, name='api_dismiss_alert')
path('<slug:slug>/api/security/alerts/<int:alert_id>/reopen/', security_views.reopen_alert, name='api_reopen_alert')
path('<slug:slug>/api/security/alerts/<int:alert_id>/fix/', security_views.create_fix_pr, name='api_create_fix_pr')
path('<slug:slug>/api/security/dependencies/<int:dependency_id>/tree/', security_views.api_dependency_tree, name='api_dependency_tree')
```

### URL Examples

```
# Security overview
https://scitex.cloud/ywatanabe/neural-decoding/security/

# All alerts
https://scitex.cloud/ywatanabe/neural-decoding/security/alerts/

# Specific alert
https://scitex.cloud/ywatanabe/neural-decoding/security/alerts/42/

# Security policy
https://scitex.cloud/ywatanabe/neural-decoding/security/policy/

# Dependencies
https://scitex.cloud/ywatanabe/neural-decoding/security/dependabot/
```

---

## API Endpoints

### 1. Trigger Security Scan

**Endpoint:** `POST /<username>/<slug>/api/security/scan/`

**Authentication:** Required (must have edit permissions)

**Response:**
```json
{
    "success": true,
    "scan_id": 123,
    "alerts": {
        "critical": 0,
        "high": 2,
        "medium": 5,
        "low": 10
    },
    "duration": 12.5
}
```

**JavaScript Example:**
```javascript
fetch('/ywatanabe/neural-decoding/api/security/scan/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': getCookie('csrftoken'),
        'Content-Type': 'application/json',
    },
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        alert(`Scan completed! Found ${data.alerts.critical} critical issues.`);
    }
});
```

### 2. Dismiss Alert

**Endpoint:** `POST /<username>/<slug>/api/security/alerts/<alert_id>/dismiss/`

**Authentication:** Required (must have edit permissions)

**Parameters:**
- `reason` (optional): Reason for dismissing

**Response:**
```json
{
    "success": true,
    "alert_id": 42,
    "status": "dismissed"
}
```

### 3. Reopen Alert

**Endpoint:** `POST /<username>/<slug>/api/security/alerts/<alert_id>/reopen/`

**Authentication:** Required (must have edit permissions)

**Response:**
```json
{
    "success": true,
    "alert_id": 42,
    "status": "open"
}
```

### 4. Create Fix PR

**Endpoint:** `POST /<username>/<slug>/api/security/alerts/<alert_id>/fix/`

**Authentication:** Required (must have edit permissions)

**Status:** Placeholder (not yet implemented)

**Planned Functionality:**
1. Create new branch
2. Update requirements.txt
3. Commit changes
4. Create PR via Gitea API

### 5. Get Dependency Tree

**Endpoint:** `GET /<username>/<slug>/api/security/dependencies/<dependency_id>/tree/`

**Authentication:** Required (must have view permissions)

**Response:**
```json
{
    "tree": {
        "name": "requests",
        "version": "2.28.0",
        "has_vulnerabilities": true,
        "children": [
            {
                "name": "urllib3",
                "version": "1.26.0",
                "has_vulnerabilities": false,
                "children": []
            }
        ]
    }
}
```

---

## Usage Guide

### For Project Owners

#### Initial Setup

1. **Navigate to Security Tab**
   ```
   https://scitex.cloud/<username>/<project>/security/
   ```

2. **Create Security Policy**
   - Go to Security → Security policy
   - Fill in contact information
   - Customize policy template
   - Save (automatically creates SECURITY.md)

3. **Run Initial Scan**
   - Click "Run security scan" button
   - Wait for scan to complete
   - Review detected alerts

#### Managing Alerts

**Triaging Alerts:**
```python
# Critical/High severity - Address immediately
# Medium severity - Plan for next sprint
# Low severity - Address when convenient
```

**Dismissing False Positives:**
1. Click on alert
2. Click "Dismiss Alert"
3. Provide reason (important for audit trail)

**Fixing Vulnerabilities:**
1. Review alert details
2. Check fixed version
3. Update requirements.txt
4. Test changes
5. Deploy
6. Alert will auto-close on next scan

#### Regular Maintenance

**Recommended Schedule:**
- **Daily**: Automated scans via Celery (future enhancement)
- **Weekly**: Review open alerts
- **Monthly**: Update security policy
- **Quarterly**: Review dependency graph

### For Contributors

#### Viewing Security Status

Even without edit permissions, contributors can:
- View all security alerts
- Read security policy
- See dependency graph
- View published advisories

#### Reporting Security Issues

1. Check project's SECURITY.md
2. Use provided contact method
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if known)

---

## Integration

### Database Migrations

1. **Create migrations:**
   ```bash
   cd /home/ywatanabe/proj/scitex-cloud
   python manage.py makemigrations project_app
   ```

2. **Apply migrations:**
   ```bash
   python manage.py migrate project_app
   ```

3. **Verify models:**
   ```bash
   python manage.py shell
   >>> from apps.project_app.models.security import SecurityAlert
   >>> SecurityAlert.objects.count()
   0
   ```

### Installing Security Tools

**Required for full functionality:**

```bash
# Dependency scanning
pip install pip-audit safety

# Secret detection
pip install detect-secrets

# Code analysis
pip install bandit

# Add to requirements.txt or pyproject.toml
echo "pip-audit>=2.6.0" >> requirements.txt
echo "detect-secrets>=1.4.0" >> requirements.txt
echo "bandit>=1.7.0" >> requirements.txt
```

### Admin Interface

Register models in admin:

```python
# apps/project_app/admin.py

from django.contrib import admin
from apps.project_app.models.security import (
    SecurityAlert,
    SecurityPolicy,
    SecurityAdvisory,
    DependencyGraph,
    SecurityScanResult,
)

@admin.register(SecurityAlert)
class SecurityAlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'severity', 'status', 'created_at']
    list_filter = ['severity', 'status', 'alert_type']
    search_fields = ['title', 'description', 'affected_package']
    date_hierarchy = 'created_at'

@admin.register(SecurityPolicy)
class SecurityPolicyAdmin(admin.ModelAdmin):
    list_display = ['project', 'contact_email', 'updated_at']
    search_fields = ['project__name', 'contact_email']

@admin.register(SecurityAdvisory)
class SecurityAdvisoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'severity', 'status', 'published_at']
    list_filter = ['severity', 'status']
    search_fields = ['title', 'cve_id']

@admin.register(DependencyGraph)
class DependencyGraphAdmin(admin.ModelAdmin):
    list_display = ['package_name', 'version', 'project', 'has_vulnerabilities']
    list_filter = ['has_vulnerabilities', 'is_direct']
    search_fields = ['package_name', 'project__name']

@admin.register(SecurityScanResult)
class SecurityScanResultAdmin(admin.ModelAdmin):
    list_display = ['project', 'scan_type', 'status', 'started_at', 'alerts_created']
    list_filter = ['scan_type', 'status']
    date_hierarchy = 'started_at'
```

### Celery Integration (Future)

For automated periodic scans:

```python
# apps/project_app/tasks.py

from celery import shared_task
from apps.project_app.models import Project
from apps.project_app.services.security_scanning import SecurityScanner

@shared_task
def run_security_scan_for_project(project_id):
    """Run security scan for a project"""
    try:
        project = Project.objects.get(id=project_id)
        scanner = SecurityScanner(project)
        results = scanner.run_full_scan()

        # Send notifications if critical/high issues found
        if results['critical'] > 0 or results['high'] > 0:
            notify_project_maintainers(project, results)

        return results
    except Exception as e:
        logger.error(f"Security scan failed for project {project_id}: {e}")
        return {'error': str(e)}

@shared_task
def run_daily_security_scans():
    """Run security scans for all active projects"""
    projects = Project.objects.filter(
        gitea_enabled=True,
        directory_created=True
    )

    for project in projects:
        run_security_scan_for_project.delay(project.id)
```

Schedule in Celery Beat:

```python
# settings.py

CELERY_BEAT_SCHEDULE = {
    'daily-security-scans': {
        'task': 'apps.project_app.tasks.run_daily_security_scans',
        'schedule': crontab(hour=2, minute=0),  # Run at 2 AM daily
    },
}
```

---

## Future Enhancements

### High Priority

1. **Automated Fix PRs**
   - Automatically create PRs to fix vulnerabilities
   - Update requirements.txt with patched versions
   - Run tests before creating PR
   - Integration with Gitea API

2. **Email Notifications**
   - Critical/high severity alerts
   - Weekly security digest
   - Advisory publications
   - Configurable per user

3. **Dependency Auto-updates (Dependabot)**
   - Automatic PR creation for outdated dependencies
   - Configurable update schedule
   - Automated testing
   - Semantic versioning awareness

4. **CVE Database Integration**
   - Real-time CVE lookups
   - Automatic severity mapping
   - Reference links
   - CVSS score display

### Medium Priority

5. **Secret Scanning in Git History**
   - Scan entire git history
   - Detect committed secrets
   - Provide rotation guidance
   - Integration with secret managers

6. **Branch Protection Integration**
   - Block merges with critical vulnerabilities
   - Require security scan pass
   - Configurable thresholds
   - Override capability for emergencies

7. **Security Metrics Dashboard**
   - Mean time to remediation
   - Open alert trends
   - Vulnerability types over time
   - Comparison with similar projects

8. **SARIF Report Export**
   - Standard format for security results
   - Integration with external tools
   - CI/CD pipeline integration
   - Compliance reporting

### Low Priority

9. **Custom Scanning Rules**
   - User-defined security checks
   - Project-specific rules
   - Rule sharing across projects
   - Community rule marketplace

10. **Vulnerability Disclosure Program**
    - Bug bounty integration
    - Researcher portal
    - Coordinated disclosure workflow
    - Hall of fame

11. **Security Score**
    - Overall security posture score
    - Gamification elements
    - Leaderboards
    - Achievement badges

12. **Multi-language Support**
    - JavaScript/Node.js (npm audit)
    - Go (gosec, govulncheck)
    - Rust (cargo-audit)
    - Java (OWASP Dependency Check)

---

## Testing

### Manual Testing Checklist

#### Security Overview
- [ ] Dashboard loads correctly
- [ ] Statistics display accurate counts
- [ ] Scan button triggers scan
- [ ] Recent alerts displayed
- [ ] Recent scans listed
- [ ] Navigation tabs work

#### Alerts
- [ ] Alert list displays
- [ ] Filters work (status, severity, type)
- [ ] Pagination works
- [ ] Alert detail page loads
- [ ] Dismiss functionality works
- [ ] Reopen functionality works

#### Security Policy
- [ ] Policy editor loads
- [ ] Can save policy
- [ ] SECURITY.md file created
- [ ] Read-only view for non-editors

#### Dependencies
- [ ] Dependency list displays
- [ ] Statistics accurate
- [ ] Vulnerability indicators shown

#### Scanning
- [ ] Dependency scan detects vulnerabilities
- [ ] Secret scan finds secrets
- [ ] Code scan identifies issues
- [ ] Scan results saved to database

### Automated Testing (Future)

```python
# apps/project_app/tests/test_security.py

from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.project_app.models import Project
from apps.project_app.models.security import SecurityAlert, SecurityPolicy
from apps.project_app.services.security_scanning import SecurityScanner

class SecurityAlertTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.user,
            slug='test-project'
        )

    def test_create_alert(self):
        alert = SecurityAlert.objects.create(
            project=self.project,
            alert_type='dependency',
            severity='high',
            title='Test vulnerability',
            description='Test description'
        )
        self.assertTrue(alert.is_open())

    def test_dismiss_alert(self):
        alert = SecurityAlert.objects.create(
            project=self.project,
            alert_type='dependency',
            severity='high',
            title='Test vulnerability'
        )
        alert.dismiss(self.user, 'False positive')
        self.assertEqual(alert.status, 'dismissed')

class SecurityViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.project = Project.objects.create(
            name='Test Project',
            owner=self.user,
            slug='test-project'
        )
        self.client.login(username='testuser', password='password')

    def test_security_overview(self):
        response = self.client.get(f'/testuser/test-project/security/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Security')

    def test_security_alerts(self):
        response = self.client.get(f'/testuser/test-project/security/alerts/')
        self.assertEqual(response.status_code, 200)
```

---

## Troubleshooting

### Common Issues

#### 1. Scan Tools Not Installed

**Error:** "Security scanning tools not installed"

**Solution:**
```bash
pip install pip-audit detect-secrets bandit
```

#### 2. Permission Denied

**Error:** "You don't have permission to view this project"

**Solution:** Check project visibility settings and user membership.

#### 3. Scan Timeout

**Error:** "Scan operation timed out"

**Solution:** Increase timeout in security_scanning.py or run scan manually on large projects.

#### 4. SECURITY.md Not Created

**Error:** "Failed to save SECURITY.md file"

**Solution:** Check project directory permissions and ensure directory_created=True.

---

## Support and Maintenance

### Monitoring

**Key Metrics to Track:**
- Scan success rate
- Average scan duration
- Alert resolution time
- False positive rate
- User engagement with security features

### Logging

Security operations are logged to:
```python
import logging
logger = logging.getLogger('apps.project_app.security')
```

**Log Levels:**
- `INFO`: Successful scans, alert creations
- `WARNING`: Scan tool not available, degraded functionality
- `ERROR`: Scan failures, database errors
- `CRITICAL`: Security breaches, system failures

### Performance Considerations

**Optimization Tips:**
1. Run scans asynchronously with Celery
2. Cache scan results for 24 hours
3. Index frequently queried fields
4. Use select_related/prefetch_related for related objects
5. Paginate large result sets

---

## Conclusion

The SciTeX security features provide comprehensive vulnerability management following GitHub's proven model. The system is designed to be:

- **Extensible**: Easy to add new scanning tools and integrations
- **Scalable**: Handles projects of any size
- **User-friendly**: Intuitive interface for both technical and non-technical users
- **Automated**: Minimal manual intervention required
- **Actionable**: Clear remediation guidance for all alerts

For questions or issues, contact the SciTeX development team or file an issue in the project repository.

---

**Document Version:** 1.0
**Last Updated:** 2025-10-24
**Author:** Claude (AI Development Agent)
**Status:** Production Ready
