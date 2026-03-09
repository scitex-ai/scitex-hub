#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Create Remote View

Create remote projects mounted via SSHFS.
"""

import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.safestring import mark_safe

from ...models import Project, RemoteCredential, RemoteProjectConfig

logger = logging.getLogger(__name__)


def create_remote_project(
    request, name, description, remote_credential_id, remote_path
):
    """
    Create a remote project (SSHFS mount, no Git).

    Args:
        request: HTTP request
        name: Project name
        description: Project description
        remote_credential_id: ID of RemoteCredential to use
        remote_path: Absolute path on remote system

    Returns:
        HTTP response (redirect or render)
    """
    # Validate inputs
    if not all([name, remote_credential_id, remote_path]):
        messages.error(request, "All fields are required for remote projects")
        return redirect("project_create")

    # Get remote credential
    try:
        credential = RemoteCredential.objects.get(
            id=remote_credential_id, user=request.user
        )
    except RemoteCredential.DoesNotExist:
        messages.error(request, "Invalid remote credential selected")
        return redirect("project_create")

    # Validate repository name
    is_valid, error_message = Project.validate_repository_name(name)
    if not is_valid:
        messages.error(request, error_message)
        return redirect("project_create")

    # Check if name already exists for this user
    if Project.objects.filter(name=name, owner=request.user).exists():
        messages.error(
            request,
            f'You already have a project named "{name}". Please choose a different name.',
        )
        return redirect("project_create")

    # Generate slug
    slug = Project.generate_unique_slug(name, owner=request.user)

    # Test SSH connection before creating project
    if not _test_ssh_connection(request, credential, remote_path):
        return redirect("project_create")

    # Create remote project
    return _create_remote_project_db(
        request, name, description, credential, remote_path, slug
    )


def _test_ssh_connection(request, credential, remote_path):
    """
    Test SSH connection to remote host via paramiko.

    Returns True if successful, False otherwise.
    """
    import paramiko

    logger.info("Testing SSH connection for remote project via paramiko")

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        client.connect(
            hostname=credential.ssh_host,
            port=credential.ssh_port,
            username=credential.ssh_username,
            key_filename=credential.private_key_path,
            timeout=10,
        )

        # Test if remote path exists
        stdin, stdout, stderr = client.exec_command(
            f'test -d "{remote_path}" && echo OK || echo NOT_FOUND'
        )
        result = stdout.read().decode().strip()

        if result == "NOT_FOUND":
            messages.warning(
                request,
                mark_safe(
                    f"Remote directory not found: <code>{remote_path}</code><br>"
                    f"The directory will be created when you access the project."
                ),
            )

        client.close()
        return True

    except paramiko.AuthenticationException:
        messages.error(
            request,
            "SSH authentication failed. Check your SSH key and credentials.",
        )
        return False
    except paramiko.SSHException as e:
        messages.error(request, f"SSH connection error: {e}")
        return False
    except TimeoutError:
        messages.error(
            request,
            "SSH connection timeout. Check your network and remote host.",
        )
        return False
    except Exception as e:
        messages.error(request, f"Connection test failed: {e}")
        return False


def _create_remote_project_db(
    request, name, description, credential, remote_path, slug
):
    """
    Create remote project in database.

    Returns HTTP response.
    """
    try:
        project = Project.objects.create(
            name=name,
            slug=slug,
            description=description,
            owner=request.user,
            project_type="remote",  # ✅ Remote project
            visibility="private",  # Remote projects default to private
        )

        # Create remote configuration
        remote_config = RemoteProjectConfig.objects.create(
            project=project,
            ssh_host=credential.ssh_host,
            ssh_port=credential.ssh_port,
            ssh_username=credential.ssh_username,
            remote_credential=credential,
            remote_path=remote_path,
            is_mounted=False,  # Not mounted yet
        )

        project.remote_config = remote_config
        project.save()

        # Update credential last used timestamp
        credential.last_used_at = timezone.now()
        credential.save()

        logger.info(
            f"✅ Remote project created: {request.user.username}/{slug} "
            f"→ {credential.ssh_username}@{credential.ssh_host}:{remote_path}"
        )

        messages.success(
            request,
            mark_safe(
                f'✅ Remote project "{name}" created successfully!<br>'
                f"Files will be accessed from: {credential.ssh_username}@{credential.ssh_host}:{remote_path}"
            ),
        )

        return redirect("project_app:detail", username=request.user.username, slug=slug)

    except Exception as e:
        logger.error(f"Failed to create remote project: {e}")
        messages.error(request, f"Failed to create remote project: {str(e)}")
        return redirect("project_create")


# EOF
