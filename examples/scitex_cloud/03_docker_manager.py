#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: examples/scitex_cloud/03_docker_manager.py

"""Example: Using DockerManager programmatically."""


from scitex_cloud import DockerManager, get_environment

print("1. Create DockerManager for dev environment:")
env = get_environment("dev")
manager = DockerManager(env=env)
print(f"   Environment: {manager.env.name}")
print(f"   Project root: {manager.project_root}")

print()
print("2. Compose file paths:")
print(f"   Compose: {manager.project_root / manager.env.compose_path}")
print(f"   Env file: {manager.project_root / manager.env.env_path}")

print()
print("3. Available operations (not executing):")
print("   - manager.build()      # Build containers")
print("   - manager.up()         # Start containers")
print("   - manager.down()       # Stop containers")
print("   - manager.restart()    # Restart containers")
print("   - manager.logs()       # Show logs")
print("   - manager.ps()         # Show status")

print()
print("4. Example: Check if compose file exists")
compose_path = manager.project_root / manager.env.compose_path
if compose_path.exists():
    print(f"   Compose file found: {compose_path}")
else:
    print(f"   Compose file not found: {compose_path}")
