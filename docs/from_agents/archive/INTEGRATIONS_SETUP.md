# SciTeX Integrations Setup Guide

This guide explains how to set up and configure the SciTeX integrations: ORCID, BibTeX Export, and Slack notifications.

## Installation

### 1. Add app to Django settings

Add `'apps.integrations_app'` to `INSTALLED_APPS` in your Django settings:

```python
INSTALLED_APPS = [
    ...
    'apps.integrations_app',
    ...
]
```

### 2. Install dependencies

```bash
pip install requests cryptography
```

### 3. Run migrations

```bash
python manage.py makemigrations integrations_app
python manage.py migrate
```

### 4. Include URLs

Add to your main `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    ...
    path('integrations/', include('apps.integrations_app.urls')),
    ...
]
```

## Configuration

### ORCID Integration

#### 1. Register your application with ORCID

1. Go to https://orcid.org/developer-tools
2. Register a new API client:
   - For development: Use the sandbox at https://sandbox.orcid.org/
   - For production: Use https://orcid.org/
3. Set the redirect URI to: `http://your-domain.com/integrations/orcid/callback/`

#### 2. Add settings to your Django configuration

Add to `settings.py`:

```python
# ORCID OAuth Configuration
ORCID_CLIENT_ID = 'your-client-id'
ORCID_CLIENT_SECRET = 'your-client-secret'
ORCID_REDIRECT_URI = 'http://your-domain.com/integrations/orcid/callback/'

# For development/sandbox:
# ORCID_CLIENT_ID = 'APP-XXXXXXXXXXXXX'
# ORCID_REDIRECT_URI = 'http://localhost:8000/integrations/orcid/callback/'
```

#### 3. Usage

Users can connect their ORCID account from the integrations dashboard:

```
/integrations/
```

Once connected, ORCID profile data is automatically synced and can be used to:
- Auto-populate author information in manuscripts
- Display researcher credentials
- Link to ORCID profile

### BibTeX Export

No additional configuration needed. BibTeX export is available for any project.

#### Usage in code

```python
from apps.integrations_app.services import BibExportService

# Export project bibliography
service = BibExportService(project)
references = [
    {
        'entry_type': 'article',
        'title': 'My Paper',
        'author': ['Smith, John', 'Doe, Jane'],
        'year': '2024',
        'journal': 'Nature',
        'volume': '123',
        'pages': '456--789',
        'doi': '10.1038/example',
    }
]

# Generate BibTeX string
bibtex_content = service.generate_bibtex(references)

# Or export to file
result = service.export_to_file(references, '/path/to/output.bib')
```

#### Add export button to project templates

```django
<a href="{% url 'integrations_app:export_project_bib' project.id %}"
   class="btn btn-primary">
    Export Bibliography (.bib)
</a>
```

### Slack Notifications

#### 1. Create a Slack Incoming Webhook

1. Go to https://api.slack.com/messaging/webhooks
2. Click "Create New App"
3. Choose "From scratch" and select your workspace
4. Go to "Incoming Webhooks" and enable it
5. Click "Add New Webhook to Workspace"
6. Choose the channel and authorize
7. Copy the webhook URL

#### 2. Configure in SciTeX

Users can configure webhooks from the integrations dashboard:

```
/integrations/slack/configure/
```

#### 3. Usage in code

Trigger notifications from your views:

```python
from apps.integrations_app.services.slack_service import (
    notify_project_created,
    notify_manuscript_updated,
    notify_analysis_completed,
)

# When a project is created
notify_project_created(project)

# When a manuscript is updated
notify_manuscript_updated(manuscript, project)

# When analysis completes
notify_analysis_completed(project, analysis_type='Data Analysis')
```

Or use the service directly:

```python
from apps.integrations_app.services import SlackService

service = SlackService(request.user)
service.send_notification('project_created', {
    'project_id': project.id,
    'project_name': project.name,
    'user': request.user.username,
    'url': project.get_absolute_url(),
})
```

## Security Considerations

### Token Encryption

OAuth tokens and API keys are encrypted before storage using Django's SCITEX_CLOUD_DJANGO_SECRET_KEY. Ensure your SCITEX_CLOUD_DJANGO_SECRET_KEY is:
- Strong and unique
- Never committed to version control
- Stored securely in production

### HTTPS

For production, always use HTTPS for:
- OAuth redirect URIs
- Webhook URLs
- API requests

### Environment Variables

Store sensitive credentials in environment variables:

```bash
# .env file (DO NOT commit to git)
ORCID_CLIENT_ID=your-client-id
ORCID_CLIENT_SECRET=your-client-secret
```

Load in settings:

```python
import os
from dotenv import load_dotenv

load_dotenv()

ORCID_CLIENT_ID = os.getenv('ORCID_CLIENT_ID')
ORCID_CLIENT_SECRET = os.getenv('ORCID_CLIENT_SECRET')
```

## Testing

### Test ORCID Integration

1. Use ORCID Sandbox for development: https://sandbox.orcid.org/
2. Create a test account
3. Connect and verify profile sync

### Test Slack Notifications

```python
from apps.integrations_app.services import SlackService

service = SlackService(user)
result = service.test_webhook(webhook_id)
```

## Troubleshooting

### ORCID Connection Issues

- Verify redirect URI matches exactly in ORCID app settings
- Check CLIENT_ID and CLIENT_SECRET are correct
- For sandbox, ensure you're using sandbox.orcid.org endpoints

### Slack Notifications Not Sending

- Verify webhook URL is correct
- Check webhook hasn't been revoked in Slack
- Ensure enabled_events includes the event type you're triggering
- Check integration logs in Django admin

### Token Expiration

ORCID tokens typically last 20 years, but if expired:
- User will need to reconnect
- System will show 'expired' status

## API Endpoints

### Get Integration Status

```
GET /integrations/api/status/
```

Returns JSON with all integration statuses for the user.

### Get ORCID Profile

```
GET /integrations/api/orcid/profile/
```

Returns JSON with ORCID profile data.

## Admin Interface

Integration connections, logs, and webhooks can be managed through Django admin:

```
/admin/integrations_app/
```

Available models:
- IntegrationConnection: View all user integrations
- ORCIDProfile: View synced ORCID profiles
- SlackWebhook: Manage webhook configurations
- IntegrationLog: View activity logs

## Future Enhancements

Planned integrations:
- GitHub/GitLab repository import
- Zotero bibliography sync
- Overleaf LaTeX export
- Google Drive file sync

See `TODOS/INTEGRATIONS.md` for the full roadmap.
