#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-11-29 07:00:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-cloud/apps/public_app/views/status/system_metrics.py
# ----------------------------------------
from __future__ import annotations
import os

__FILE__ = "./apps/public_app/views/status/system_metrics.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
System Metrics Collection

CPU, Memory, GPU, Disk I/O, and Network metrics.
"""

import subprocess

import psutil


def check_system_resources(status_data):
    """Check system resource usage."""
    try:
        # CPU information
        cpu_count = psutil.cpu_count(logical=False) or psutil.cpu_count()
        cpu_count_logical = psutil.cpu_count(logical=True)

        # Try to get CPU name from /proc/cpuinfo (Linux)
        cpu_name = get_cpu_name()

        # GPU information
        gpu_info = get_gpu_info(cpu_name)

        # Disk I/O stats
        disk_io = psutil.disk_io_counters()
        disk_read_mb = round(disk_io.read_bytes / (1024**2), 2) if disk_io else 0
        disk_write_mb = round(disk_io.write_bytes / (1024**2), 2) if disk_io else 0

        # Network I/O stats
        net_io = psutil.net_io_counters()
        net_sent_mb = round(net_io.bytes_sent / (1024**2), 2) if net_io else 0
        net_recv_mb = round(net_io.bytes_recv / (1024**2), 2) if net_io else 0

        status_data["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "cpu_cores": cpu_count,
            "cpu_cores_logical": cpu_count_logical,
            "cpu_name": cpu_name,
            "memory_percent": psutil.virtual_memory().percent,
            "memory_available_gb": round(psutil.virtual_memory().available / (1024**3), 1),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "gpu_info": gpu_info,
            "disk_read_mb": disk_read_mb,
            "disk_write_mb": disk_write_mb,
            "net_sent_mb": net_sent_mb,
            "net_recv_mb": net_recv_mb,
        }
    except Exception as e:
        status_data["system"] = {"error": str(e)}


def get_cpu_name():
    """Get CPU name from /proc/cpuinfo (Linux)."""
    cpu_name = "Unknown"
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if 'model name' in line:
                    cpu_name = line.split(':')[1].strip()
                    break
    except:
        pass
    return cpu_name


def get_gpu_info(cpu_name):
    """Get GPU information from various sources."""
    gpu_info = "None available"
    try:
        # Try NVIDIA first
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except:
            pass

        # If no NVIDIA GPU, check CPU info for integrated graphics
        if cpu_name and ('Radeon Graphics' in cpu_name or 'Intel' in cpu_name):
            if 'Radeon Graphics' in cpu_name:
                return "AMD Radeon Graphics (Integrated)"
            elif 'Intel' in cpu_name and 'Graphics' in cpu_name:
                return "Intel Integrated Graphics"

        # Try AMD/other GPUs via lspci
        try:
            result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'VGA compatible controller' in line or 'Display controller' in line:
                        parts = line.split(': ', 1)
                        if len(parts) > 1:
                            return parts[1].strip()
        except:
            pass
    except:
        pass

    return gpu_info


# EOF
