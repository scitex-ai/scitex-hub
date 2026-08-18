"""Slack webhook notification service"""

import requests
import json
from django.core.exceptions import ValidationError
from django.utils import timezone
from ..models import IntegrationConnection, SlackWebhook, IntegrationLog
from .webhook_security import validate_slack_webhook_url


class SlackService:
    """Service for sending Slack webhook notifications"""

    def __init__(self, user):
        self.user = user

    def create_webhook(
        self, webhook_url, channel="", enabled_events=None, project_ids=None
    ):
        """
        Create or update Slack webhook configuration

        Args:
            webhook_url: Slack webhook URL
            channel: Optional channel override
            enabled_events: List of event types to notify
            project_ids: Optional list of project IDs to filter

        Returns:
            SlackWebhook: Created webhook instance

        Raises:
            ValidationError: If webhook_url is not an https://hooks.slack.com/...
                URL. Enforced BEFORE any row is stored (SSRF, py/full-ssrf);
                the caller surfaces the error to the user (no silent fallback).
        """
        # SSRF guard (fail-closed): reject non-Slack hosts before persisting.
        validate_slack_webhook_url(webhook_url)

        # Get or create integration connection
        connection, created = IntegrationConnection.objects.get_or_create(
            user=self.user, service="slack", defaults={"status": "active"}
        )

        if enabled_events is None:
            enabled_events = [
                "project_created",
                "manuscript_updated",
                "analysis_completed",
            ]

        # Create webhook
        webhook = SlackWebhook.objects.create(
            connection=connection,
            webhook_url=webhook_url,
            channel=channel,
            enabled_events=enabled_events,
        )

        # Add project filters if specified
        if project_ids:
            from apps.infra.project_app.models import Project

            projects = Project.objects.filter(id__in=project_ids, owner=self.user)
            webhook.project_filter.set(projects)

        self._log_activity(
            connection,
            "connect",
            f"Slack webhook created for channel: {channel or 'default'}",
        )

        return webhook

    def send_notification(self, event_type, data):
        """
        Send notification to all configured webhooks

        Args:
            event_type: Type of event (e.g., 'project_created')
            data: Event data dict

        Returns:
            dict: Results of notification attempts
        """
        try:
            connection = IntegrationConnection.objects.get(
                user=self.user, service="slack", status="active"
            )
        except IntegrationConnection.DoesNotExist:
            return {"success": False, "error": "No active Slack integration"}

        results = []
        webhooks = connection.slack_webhooks.filter(is_active=True)

        for webhook in webhooks:
            # Check if event is enabled
            if event_type not in webhook.enabled_events:
                continue

            # Check project filter
            project_id = data.get("project_id")
            if webhook.project_filter.exists() and project_id:
                if not webhook.project_filter.filter(id=project_id).exists():
                    continue

            # Send notification
            result = self._send_webhook(webhook, event_type, data)
            results.append(result)

            # Update webhook stats
            if result["success"]:
                webhook.notification_count += 1
                webhook.last_notification_at = timezone.now()
                webhook.save()

        return {
            "success": any(r["success"] for r in results),
            "results": results,
            "sent_count": sum(1 for r in results if r["success"]),
        }

    def _send_webhook(self, webhook, event_type, data):
        """Send single webhook notification"""
        # SSRF guard (fail-closed) at the true security boundary: this catches
        # rows created via admin / migration / direct ORM that never passed
        # through create_webhook. On a bad host we do NOT post (py/full-ssrf).
        # Bind the RETURN value and post THAT. The validator returns the url
        # unchanged precisely so callers can do this ("so callers can inline
        # the check" — its docstring). Discarding it and posting
        # `webhook.webhook_url` again made the checked expression and the sent
        # expression two different reads of a mutable attribute: correct today,
        # and silently wrong the moment anything reloads or mutates the row
        # between the guard and the post. It also left the dataflow invisible
        # to CodeQL, which is why py/full-ssrf #9058 stayed open on a finding
        # that was genuinely fixed.
        try:
            safe_webhook_url = validate_slack_webhook_url(webhook.webhook_url)
        except ValidationError as exc:
            error_message = "; ".join(exc.messages)
            self._log_error(webhook.connection, "notify", error_message)
            return {
                "success": False,
                "webhook_id": webhook.id,
                "error": error_message,
            }

        try:
            # Build message
            message = self._build_message(event_type, data)

            # Add channel override if specified
            if webhook.channel:
                message["channel"] = webhook.channel

            # Add username and icon
            message["username"] = webhook.username
            message["icon_emoji"] = webhook.icon_emoji

            # Send request
            response = requests.post(
                safe_webhook_url,
                data=json.dumps(message),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            success = response.status_code == 200

            if success:
                self._log_activity(
                    webhook.connection, "notify", f"Sent {event_type} notification"
                )
            else:
                self._log_error(
                    webhook.connection,
                    "notify",
                    f"Failed to send notification: {response.text}",
                )

            return {
                "success": success,
                "webhook_id": webhook.id,
                "status_code": response.status_code,
            }

        except Exception as e:
            self._log_error(webhook.connection, "notify", str(e))
            return {
                "success": False,
                "webhook_id": webhook.id,
                "error": str(e),
            }

    def _build_message(self, event_type, data):
        """Build Slack message payload"""
        # Message templates for different events
        templates = {
            "project_created": {
                "text": f"🆕 New project created: *{data.get('project_name')}*",
                "color": "good",
            },
            "project_updated": {
                "text": f"📝 Project updated: *{data.get('project_name')}*",
                "color": "#439FE0",
            },
            "manuscript_updated": {
                "text": f"📄 Manuscript updated: *{data.get('manuscript_title')}*",
                "color": "#439FE0",
            },
            "analysis_completed": {
                "text": f"✅ Analysis completed for: *{data.get('project_name')}*",
                "color": "good",
            },
            "figures_generated": {
                "text": f"📊 Figures generated for: *{data.get('project_name')}*",
                "color": "good",
            },
        }

        template = templates.get(
            event_type,
            {
                "text": f"📢 Event: {event_type}",
                "color": "warning",
            },
        )

        # Build attachment
        attachment = {
            "fallback": template["text"],
            "color": template["color"],
            "title": data.get("title", template["text"]),
            "fields": [],
            "footer": "SciTeX",
            "ts": int(timezone.now().timestamp()),
        }

        # Add relevant fields based on data
        if data.get("project_name"):
            attachment["fields"].append(
                {
                    "title": "Project",
                    "value": data["project_name"],
                    "short": True,
                }
            )

        if data.get("user"):
            attachment["fields"].append(
                {
                    "title": "User",
                    "value": data["user"],
                    "short": True,
                }
            )

        if data.get("description"):
            attachment["fields"].append(
                {
                    "title": "Description",
                    "value": data["description"],
                    "short": False,
                }
            )

        if data.get("url"):
            attachment["title_link"] = data["url"]

        return {
            "text": template["text"],
            "attachments": [attachment],
        }

    def test_webhook(self, webhook_id):
        """Send test notification to webhook"""
        try:
            webhook = SlackWebhook.objects.get(
                id=webhook_id, connection__user=self.user
            )

            test_data = {
                "project_name": "Test Project",
                "user": self.user.username,
                "description": "This is a test notification from SciTeX",
            }

            result = self._send_webhook(webhook, "project_created", test_data)
            return result

        except SlackWebhook.DoesNotExist:
            return {"success": False, "error": "Webhook not found"}

    def delete_webhook(self, webhook_id):
        """Delete webhook configuration"""
        try:
            webhook = SlackWebhook.objects.get(
                id=webhook_id, connection__user=self.user
            )
            webhook.delete()
            return {"success": True}

        except SlackWebhook.DoesNotExist:
            return {"success": False, "error": "Webhook not found"}

    def _log_activity(self, connection, action, details):
        """Log successful activity"""
        IntegrationLog.objects.create(
            connection=connection, action=action, details=details, success=True
        )

    def _log_error(self, connection, action, error_message):
        """Log error"""
        IntegrationLog.objects.create(
            connection=connection,
            action=action,
            error_message=error_message,
            success=False,
        )


# Convenience functions for triggering notifications
def notify_project_created(project):
    """Send notification when project is created"""
    service = SlackService(project.owner)
    return service.send_notification(
        "project_created",
        {
            "project_id": project.id,
            "project_name": project.name,
            "user": project.owner.username,
            "url": (
                project.get_absolute_url()
                if hasattr(project, "get_absolute_url")
                else ""
            ),
        },
    )


def notify_manuscript_updated(manuscript, project):
    """Send notification when manuscript is updated"""
    service = SlackService(project.owner)
    return service.send_notification(
        "manuscript_updated",
        {
            "project_id": project.id,
            "project_name": project.name,
            "manuscript_title": getattr(manuscript, "title", "Untitled"),
            "user": project.owner.username,
        },
    )


def notify_analysis_completed(project, analysis_type=""):
    """Send notification when analysis is completed"""
    service = SlackService(project.owner)
    return service.send_notification(
        "analysis_completed",
        {
            "project_id": project.id,
            "project_name": project.name,
            "user": project.owner.username,
            "description": f"Analysis type: {analysis_type}" if analysis_type else "",
        },
    )
