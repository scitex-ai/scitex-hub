"""
Project Signal Handlers
Contains: Signal handlers for Project model
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging


logger = logging.getLogger(__name__)


# Currently, no signals are defined in the original project.py
# This file is created for future signal handlers

# Example signal structure (commented out):
#
# @receiver(post_save, sender='project_app.Project')
# def project_post_save(sender, instance, created, **kwargs):
#     """Handle post-save actions for Project"""
#     if created:
#         logger.info(f"New project created: {instance.name}")
#
# @receiver(post_delete, sender='project_app.Project')
# def project_post_delete(sender, instance, **kwargs):
#     """Handle post-delete actions for Project"""
#     logger.info(f"Project deleted: {instance.name}")
