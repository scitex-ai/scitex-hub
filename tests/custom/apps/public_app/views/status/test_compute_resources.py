#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/public_app/views/status/compute_resources.py"""

import pytest

# from apps.infra.public_app.views.status.compute_resources import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder_pending_implementation(self):
        """Placeholder test - implement actual tests."""
        # Arrange
        # Act
        # Assert
        pytest.skip("Not implemented yet")


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/public_app/views/status/compute_resources.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# # Timestamp: "2025-11-29 07:00:00 (ywatanabe)"
# # File: /home/ywatanabe/proj/scitex-hub/apps/public_app/views/status/compute_resources.py
# # ----------------------------------------
# from __future__ import annotations
# import os
#
# __FILE__ = "./apps/public_app/views/status/compute_resources.py"
# __DIR__ = os.path.dirname(__FILE__)
# # ----------------------------------------
#
# """
# Compute Resources Status
#
# SLURM cluster and Apptainer/Singularity container runtime checks.
# """
#
# import logging
# import subprocess
#
# logger = logging.getLogger("scitex")
#
#
# def check_slurm_status(status_data):
#     """
#     Check SLURM cluster status with comprehensive terminal functionality test.
#
#     Tests:
#     1. sinfo responds (SLURM services running)
#     2. scitex user (UID 1000) exists on host
#     3. SLURM can actually execute jobs as scitex user
#     """
#     checks = {
#         "sinfo": False,
#         "scitex_user": False,
#         "job_execution": False,
#     }
#
#     try:
#         # Test 1: Use sinfo to check if SLURM is responding
#         result = subprocess.run(
#             ['sinfo', '--noheader', '-o', '%P %a %D %t'],
#             capture_output=True, text=True, timeout=5
#         )
#         checks["sinfo"] = result.returncode == 0 and result.stdout.strip()
#
#         # Test 2: Check if scitex user (UID 1000) exists on host
#         try:
#             uid_check = subprocess.run(
#                 ['id', '-u', 'scitex'],
#                 capture_output=True, text=True, timeout=2
#             )
#             checks["scitex_user"] = uid_check.returncode == 0 and uid_check.stdout.strip() == "1000"
#         except Exception:
#             pass
#
#         # Test 3: Skip SLURM job execution test in health check API
#         # This test is too slow for the header health indicator.
#         # If sinfo works and scitex user exists, assume job execution works.
#         # Detailed job execution testing is done on the server-status page.
#         if checks["sinfo"] and checks["scitex_user"]:
#             checks["job_execution"] = True  # Assume OK if prerequisites pass
#
#         # Determine overall health
#         all_checks_pass = all(checks.values())
#         is_up = checks["sinfo"]  # At minimum, sinfo must work
#
#         # Build detailed message
#         details = []
#         if checks["sinfo"]:
#             details.append("✓ SLURM services responding")
#         else:
#             details.append("✗ SLURM services not responding")
#
#         if checks["scitex_user"]:
#             details.append("✓ scitex user (UID 1000) exists")
#         else:
#             details.append("✗ scitex user (UID 1000) missing")
#
#         if checks["job_execution"]:
#             details.append("✓ Terminal functionality verified")
#         elif checks["sinfo"] and checks["scitex_user"]:
#             details.append("✗ Job execution failed (SLURM may need restart)")
#
#         status_data["slurm"] = {
#             "is_running": is_up,
#             "status": "running" if is_up else "down",
#             "health_class": "healthy" if all_checks_pass else ("warning" if is_up else "unhealthy"),
#             "message": " | ".join(details),
#             "partitions": result.stdout.strip() if checks["sinfo"] else None,
#             "checks": checks,  # For detailed tooltip
#         }
#
#         # Get job queue info if SLURM is up
#         if is_up:
#             try:
#                 squeue_result = subprocess.run(
#                     ['squeue', '--noheader', '-o', '%i %P %j %u %t %M'],
#                     capture_output=True, text=True, timeout=5
#                 )
#                 status_data["slurm"]["jobs"] = squeue_result.stdout.strip() or "No jobs running"
#             except Exception:
#                 pass
#
#     except FileNotFoundError:
#         status_data["slurm"] = {
#             "is_running": False,
#             "status": "not installed",
#             "health_class": "down",
#             "error": "SLURM not installed",
#             "checks": checks,
#         }
#     except Exception as e:
#         status_data["slurm"] = {
#             "is_running": False,
#             "status": "error",
#             "health_class": "unhealthy",
#             "error": str(e),
#             "checks": checks,
#         }
#
#
# def check_container_runtime_status(status_data):
#     """
#     Check Apptainer/Singularity container runtime status through SLURM.
#
#     Tests:
#     1. Container command exists (apptainer or singularity)
#     2. Can actually execute a container through SLURM (how it's really used)
#     """
#     try:
#         # Try apptainer first, then singularity
#         container_cmd = None
#         version = None
#         can_execute = False
#
#         for cmd in ['apptainer', 'singularity']:
#             try:
#                 # Test 1: Check version (fast check only)
#                 result = subprocess.run(
#                     [cmd, '--version'],
#                     capture_output=True, text=True, timeout=2
#                 )
#                 if result.returncode == 0:
#                     container_cmd = cmd
#                     version = result.stdout.strip()
#                     # Skip slow SLURM execution test for health check API
#                     # If command exists, assume it works.
#                     can_execute = True
#                     break
#             except FileNotFoundError:
#                 continue
#
#         if container_cmd:
#             status_data["apptainer"] = {
#                 "is_running": True,
#                 "status": "available" if can_execute else "limited",
#                 "health_class": "healthy" if can_execute else "warning",
#                 "command": container_cmd,
#                 "version": version,
#                 "can_execute": can_execute,
#                 "message": "✓ Container runtime functional via SLURM" if can_execute else "⚠ Runtime installed but SLURM execution untested",
#             }
#         else:
#             status_data["apptainer"] = {
#                 "is_running": False,
#                 "status": "not installed",
#                 "health_class": "down",
#                 "error": "Apptainer/Singularity not installed",
#             }
#     except Exception as e:
#         status_data["apptainer"] = {
#             "is_running": False,
#             "status": "error",
#             "health_class": "unhealthy",
#             "error": str(e),
#         }
#
#
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/public_app/views/status/compute_resources.py
# --------------------------------------------------------------------------------
