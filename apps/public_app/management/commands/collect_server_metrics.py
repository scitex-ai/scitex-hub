#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Management command to collect and store server metrics.

Usage:
    python manage.py collect_server_metrics --interval 5
    python manage.py collect_server_metrics --once
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.public_app.models import ServerMetrics
import psutil
import time
import logging
import socket

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Collect server performance metrics and store in database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=5,
            help="Collection interval in seconds (default: 5)",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Collect metrics once and exit",
        )
        parser.add_argument(
            "--retention-days",
            type=int,
            default=30,
            help="Days to keep metrics (default: 30, older records deleted)",
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        once = options["once"]
        retention_days = options["retention_days"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting metrics collection (interval: {interval}s, retention: {retention_days} days)"
            )
        )

        try:
            if once:
                self._collect_metrics(retention_days)
                self.stdout.write(self.style.SUCCESS("Metrics collected successfully"))
            else:
                while True:
                    self._collect_metrics(retention_days)
                    time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nMetrics collection stopped"))

    def _collect_metrics(self, retention_days):
        """Collect and store current server metrics."""
        try:
            # Get CPU info
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count(logical=False) or psutil.cpu_count()
            cpu_count_logical = psutil.cpu_count(logical=True)

            # Get memory info
            memory = psutil.virtual_memory()
            memory_used_gb = round((memory.total - memory.available) / (1024**3), 2)

            # Get disk info
            disk = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()

            # Get network info
            net_io = psutil.net_io_counters()

            # Check service statuses
            ssh_gateway_status = self._check_port(2200)
            gitea_ssh_status = self._check_port(2222)

            # Check database
            from django.db import connection
            database_status = False
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                database_status = True
            except:
                pass

            # Check Redis
            redis_status = False
            try:
                from django.core.cache import cache
                cache.set('health_check', 'ok', 10)
                redis_status = cache.get('health_check') == 'ok'
            except:
                pass

            # Check Docker services
            docker_services_running = None
            try:
                import docker
                client = docker.from_env()
                containers = client.containers.list()
                docker_services_running = len(containers)
            except:
                pass

            # Get visitor pool status
            visitor_pool_allocated = None
            visitor_pool_total = None
            try:
                from apps.project_app.services.visitor_pool import VisitorPool
                pool_status = VisitorPool.get_pool_status()
                visitor_pool_allocated = pool_status['allocated']
                visitor_pool_total = pool_status['total']
            except Exception as e:
                logger.debug(f"Could not get visitor pool status: {e}")

            # Count active logged-in users (with valid sessions in last 15 minutes)
            active_users_count = None
            try:
                from django.contrib.sessions.models import Session
                from django.contrib.auth import get_user_model
                User = get_user_model()

                # Get all active sessions (not expired)
                active_sessions = Session.objects.filter(expire_date__gte=timezone.now())

                # Count unique logged-in users from active sessions
                user_ids = set()
                for session in active_sessions:
                    session_data = session.get_decoded()
                    user_id = session_data.get('_auth_user_id')
                    if user_id:
                        user_ids.add(user_id)

                active_users_count = len(user_ids)
            except Exception as e:
                logger.debug(f"Could not get active users count: {e}")

            # Create metrics record
            ServerMetrics.objects.create(
                timestamp=timezone.now(),
                cpu_percent=cpu_percent,
                cpu_cores=cpu_count,
                cpu_cores_logical=cpu_count_logical,
                memory_percent=memory.percent,
                memory_used_gb=memory_used_gb,
                memory_total_gb=round(memory.total / (1024**3), 2),
                memory_available_gb=round(memory.available / (1024**3), 2),
                disk_percent=disk.percent,
                disk_used_gb=round(disk.used / (1024**3), 2),
                disk_total_gb=round(disk.total / (1024**3), 2),
                disk_read_mb=round(disk_io.read_bytes / (1024**2), 2) if disk_io else 0,
                disk_write_mb=round(disk_io.write_bytes / (1024**2), 2) if disk_io else 0,
                net_sent_mb=round(net_io.bytes_sent / (1024**2), 2),
                net_recv_mb=round(net_io.bytes_recv / (1024**2), 2),
                docker_services_running=docker_services_running,
                ssh_gateway_status=ssh_gateway_status,
                gitea_ssh_status=gitea_ssh_status,
                database_status=database_status,
                redis_status=redis_status,
                visitor_pool_allocated=visitor_pool_allocated,
                visitor_pool_total=visitor_pool_total,
                active_users_count=active_users_count,
            )

            # Clean up old records
            cutoff_date = timezone.now() - timezone.timedelta(days=retention_days)
            deleted_count, _ = ServerMetrics.objects.filter(timestamp__lt=cutoff_date).delete()
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} old metric records (older than {retention_days} days)")

            logger.debug(f"Collected metrics: CPU={cpu_percent}%, Memory={memory.percent}%, Disk={disk.percent}%")

        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}", exc_info=True)
            self.stdout.write(self.style.ERROR(f"Error collecting metrics: {e}"))

    def _check_port(self, port, host="127.0.0.1", timeout=1):
        """Check if a port is open/accessible."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
