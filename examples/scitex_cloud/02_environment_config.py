#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: examples/scitex_cloud/02_environment_config.py

"""Example: Working with environment configurations."""

from scitex_cloud import get_environment
from scitex_cloud.config.environments import ENVIRONMENTS

print("1. List available environments:")
for name, env in ENVIRONMENTS.items():
    print(f"   - {name}: {env.description}")

print()
print("2. Get dev environment:")
dev_env = get_environment("dev")
print(f"   Name: {dev_env.name}")
print(f"   Host: {dev_env.host}")
print(f"   Port: {dev_env.port}")
print(f"   Env file: {dev_env.env_path}")
print(f"   Compose file: {dev_env.compose_path}")

print()
print("3. Get prod environment:")
prod_env = get_environment("prod")
print(f"   Name: {prod_env.name}")
print(f"   Host: {prod_env.host}")
print(f"   Port: {prod_env.port}")

print()
print("4. Auto-detect environment (defaults to dev):")
auto_env = get_environment()
print(f"   Detected: {auto_env.name}")
