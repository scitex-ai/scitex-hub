#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for apps/public_app/tool_repo_concat_api.py"""

import pytest

# from apps.infra.public_app.tool_repo_concat_api import ...


class TestPlaceholder:
    """Placeholder test class - replace with actual tests."""

    def test_placeholder(self):
        """Placeholder test - implement actual tests."""
        pytest.skip("Not implemented yet")


if __name__ == "__main__":
    import os

    import pytest

    pytest.main([os.path.abspath(__file__)])

# --------------------------------------------------------------------------------
# Start of Source Code from: apps/public_app/tool_repo_concat_api.py
# --------------------------------------------------------------------------------
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# # Timestamp: "2025-11-17"
# # File: /home/ywatanabe/proj/scitex-hub/apps/public_app/views/tool_repo_concat_api.py
# # ----------------------------------------
# """
# Repository Concatenator Tool - API Endpoints
#
# Handles cloning Git repositories and concatenating files.
# """
#
# from __future__ import annotations
#
# import logging
# import shutil
# import subprocess
# import tempfile
# import re
# import os
# from pathlib import Path
# from typing import Set, Tuple, Optional
# import json
#
# from django.http import JsonResponse
# from django.views.decorators.http import require_http_methods
# from django.views.decorators.csrf import csrf_exempt
#
# logger = logging.getLogger(__name__)
#
# # Store temp paths for cleanup (in production, use Redis/cache)
# _temp_repos = {}
#
#
# def _get_user_ssh_key(user) -> Optional[Path]:
#     """
#     Get user's SSH private key path.
#
#     NEW SYSTEM: SSH keys are stored in user's home directory:
#     ./data/users/{username}/.ssh/
#
#     This allows:
#     - Multiple SSH keys per user
#     - Standard Unix-like structure
#     - User can manage their own keys (CRUD)
#
#     Returns path to private key if exists, None otherwise.
#     """
#     from django.conf import settings
#     from apps.infra.project_app.services.project_filesystem import get_project_filesystem_manager
#
#     # Get user's home directory
#     manager = get_project_filesystem_manager(user)
#     # manager.base_path = data/users/{username}/proj/
#     # So parent = data/users/{username}/
#     user_home = manager.base_path.parent
#     ssh_dir = user_home / '.ssh'
#
#     logger.error(f"DEBUG _get_user_ssh_key: user={user.username}, user_id={user.id}")
#     logger.error(f"DEBUG user_home={user_home}, ssh_dir={ssh_dir}")
#     logger.error(f"DEBUG ssh_dir exists: {ssh_dir.exists()}")
#
#     if ssh_dir.exists():
#         contents = list(ssh_dir.iterdir())
#         logger.error(f"DEBUG ssh_dir contents: {contents}")
#     else:
#         logger.error(f"DEBUG ssh_dir does NOT exist, creating it...")
#         ssh_dir.mkdir(parents=True, exist_ok=True)
#         os.chmod(ssh_dir, 0o700)
#         logger.error(f"DEBUG Created ssh_dir: {ssh_dir}")
#
#     # Common SSH key types (in order of preference)
#     ssh_key_names = ['id_ed25519', 'id_rsa', 'id_ecdsa']
#
#     for key_name in ssh_key_names:
#         key_path = ssh_dir / key_name
#         logger.error(f"DEBUG checking: {key_path}, exists={key_path.exists()}")
#         if key_path.exists():
#             logger.error(f"DEBUG Found SSH key: {key_path}")
#             return key_path
#
#     # FALLBACK: Check old centralized location for backward compatibility
#     old_ssh_dir = Path(settings.BASE_DIR) / "data" / "ssh_keys" / f"user_{user.id}"
#     logger.error(f"DEBUG Fallback: checking old location {old_ssh_dir}")
#
#     if old_ssh_dir.exists():
#         for key_name in ssh_key_names:
#             old_key_path = old_ssh_dir / key_name
#             if old_key_path.exists():
#                 logger.error(f"DEBUG Found key in old location, copying to new location: {old_key_path}")
#                 # Copy to new location
#                 import shutil
#                 new_key_path = ssh_dir / key_name
#                 new_pub_path = ssh_dir / f"{key_name}.pub"
#                 old_pub_path = old_ssh_dir / f"{key_name}.pub"
#
#                 shutil.copy2(old_key_path, new_key_path)
#                 if old_pub_path.exists():
#                     shutil.copy2(old_pub_path, new_pub_path)
#
#                 os.chmod(new_key_path, 0o600)
#                 if new_pub_path.exists():
#                     os.chmod(new_pub_path, 0o644)
#
#                 logger.error(f"DEBUG Migrated SSH key to {new_key_path}")
#                 return new_key_path
#
#     logger.error(f"DEBUG No SSH key found for {user.username} in {ssh_dir} or {old_ssh_dir}")
#     return None
#
#
# def _convert_https_to_ssh(https_url: str) -> str:
#     """
#     Convert HTTPS Git URL to SSH format.
#
#     Examples:
#     - https://github.com/user/repo.git -> git@github.com:user/repo.git
#     - https://gitlab.com/user/repo.git -> git@gitlab.com:user/repo.git
#     """
#     # GitHub
#     pattern = r'https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$'
#     match = re.match(pattern, https_url)
#     if match:
#         user, repo = match.groups()
#         return f'git@github.com:{user}/{repo}.git'
#
#     # GitLab
#     pattern = r'https?://gitlab\.com/([^/]+)/([^/]+?)(?:\.git)?$'
#     match = re.match(pattern, https_url)
#     if match:
#         user, repo = match.groups()
#         return f'git@gitlab.com:{user}/{repo}.git'
#
#     # Bitbucket
#     pattern = r'https?://bitbucket\.org/([^/]+)/([^/]+?)(?:\.git)?$'
#     match = re.match(pattern, https_url)
#     if match:
#         user, repo = match.groups()
#         return f'git@bitbucket.org:{user}/{repo}.git'
#
#     return https_url
#
#
# def parse_github_url(url: str) -> Tuple[str, Optional[str], Optional[str]]:
#     """
#     Parse GitHub URL to extract repo URL, branch, and subdirectory.
#
#     Examples:
#     - https://github.com/user/repo -> (https://github.com/user/repo.git, None, None)
#     - https://github.com/user/repo/tree/main/path -> (https://github.com/user/repo.git, main, path)
#     - git@github.com:user/repo.git -> (git@github.com:user/repo.git, None, None)
#
#     Returns: (git_url, branch, subdirectory)
#     """
#     # Handle SSH URLs
#     if url.startswith('git@'):
#         return (url, None, None)
#
#     # Handle HTTPS URLs with subdirectory
#     # Pattern: https://github.com/user/repo/tree/branch/path/to/dir
#     pattern = r'https?://github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+)/(.+))?'
#     match = re.match(pattern, url)
#
#     if match:
#         user, repo, branch, subdir = match.groups()
#         # Remove .git if present
#         repo = repo.replace('.git', '')
#         git_url = f'https://github.com/{user}/{repo}.git'
#         return (git_url, branch, subdir)
#
#     # GitLab pattern
#     pattern_gitlab = r'https?://gitlab\.com/([^/]+)/([^/]+)(?:/-/tree/([^/]+)/(.+))?'
#     match = re.match(pattern_gitlab, url)
#     if match:
#         user, repo, branch, subdir = match.groups()
#         repo = repo.replace('.git', '')
#         git_url = f'https://gitlab.com/{user}/{repo}.git'
#         return (git_url, branch, subdir)
#
#     # Simple URL without subdirectory
#     if url.endswith('.git'):
#         return (url, None, None)
#     else:
#         return (url + '.git' if not url.endswith('.git') else url, None, None)
#
#
# @require_http_methods(["POST"])
# def api_clone_and_analyze(request):
#     """
#     Clone a Git repository and analyze file extensions.
#
#     POST data:
#     - repo_url: Git repository URL (supports subdirectory URLs like github.com/user/repo/tree/branch/path)
#     - use_ssh: Whether to use SSH authentication (default: auto-detect from URL)
#
#     Returns:
#     - temp_path: Path to cloned repository
#     - extensions: List of file extensions found
#     - file_count: Total number of files
#     - subdirectory: Subdirectory path if specified
#     - branch: Branch name if specified
#     """
#     try:
#         data = json.loads(request.body)
#         original_url = data.get('repo_url', '').strip()
#         use_ssh = data.get('use_ssh', False)
#
#         if not original_url:
#             return JsonResponse({'error': 'Repository URL is required'}, status=400)
#
#         # Parse URL to extract git_url, branch, and subdirectory
#         git_url, branch, subdirectory = parse_github_url(original_url)
#
#         # Validate URL
#         is_ssh = git_url.startswith('git@')
#         if not is_ssh and not any(domain in git_url for domain in ['github.com', 'gitlab.com', 'bitbucket.org']):
#             return JsonResponse(
#                 {'error': 'Only GitHub, GitLab, and Bitbucket URLs are supported'},
#                 status=400
#             )
#
#         # Auto-convert HTTPS to SSH if user wants SSH
#         if use_ssh and not is_ssh and git_url.startswith('https://'):
#             git_url = _convert_https_to_ssh(git_url)
#             is_ssh = True
#             logger.error(f"DEBUG: Auto-converted HTTPS to SSH: {git_url}")
#
#         # If using SSH, get user's SSH key
#         ssh_key_path = None
#         logger.error(f"DEBUG: use_ssh={use_ssh}, is_ssh={is_ssh}, git_url={git_url}")
#
#         if is_ssh:
#             if request.user.is_authenticated:
#                 # Get user's SSH key from profile/settings
#                 logger.error(f"DEBUG: Looking for SSH key for user {request.user.username} (id={request.user.id})")
#                 ssh_key_path = _get_user_ssh_key(request.user)
#                 logger.error(f"DEBUG: SSH key lookup result: {ssh_key_path}")
#
#                 if not ssh_key_path:
#                     return JsonResponse({
#                         'error': 'SSH key not found in ~/.ssh/',
#                         'help': 'Please add your SSH key:\n1. Generate key: ssh-keygen -t ed25519\n2. Add to GitHub: https://github.com/settings/keys\n3. Upload to SciTeX: Account Settings',
#                         'settings_url': f'/{request.user.username}/settings/',
#                         'debug_user_id': request.user.id,
#                         'debug_username': request.user.username,
#                     }, status=400)
#             else:
#                 return JsonResponse(
#                     {'error': 'Authentication required for SSH access. Please login.'},
#                     status=401
#                 )
#
#         # Create temporary directory
#         temp_dir = tempfile.mkdtemp(prefix='scitex_repo_')
#         temp_path = Path(temp_dir)
#
#         try:
#             # Build git clone command
#             clone_cmd = ['git', 'clone', '--depth', '1']
#
#             # Add branch if specified
#             if branch:
#                 clone_cmd.extend(['--branch', branch])
#
#             clone_cmd.extend([git_url, str(temp_path)])
#
#             # Setup SSH environment if needed
#             env = os.environ.copy()
#             if ssh_key_path:
#                 env['GIT_SSH_COMMAND'] = f'ssh -i {ssh_key_path} -o StrictHostKeyChecking=no'
#
#             # Clone repository
#             result = subprocess.run(
#                 clone_cmd,
#                 capture_output=True,
#                 text=True,
#                 timeout=60,
#                 env=env,
#             )
#
#             if result.returncode != 0:
#                 shutil.rmtree(temp_path, ignore_errors=True)
#                 error_msg = result.stderr[:500] if result.stderr else 'Clone failed'
#
#                 # Check for authentication/permission errors
#                 if any(phrase in error_msg.lower() for phrase in [
#                     'could not read username',
#                     'could not read password',
#                     'authentication failed',
#                     'permission denied',
#                 ]):
#                     return JsonResponse({
#                         'error': 'Authentication failed',
#                         'help': 'Your SSH key may not be added to GitHub.\n\nAdd this public key to GitHub:\nhttps://github.com/settings/keys',
#                         'detail': error_msg
#                     }, status=403)
#
#                 # Repository not found
#                 if 'not found' in error_msg.lower() or '404' in error_msg:
#                     return JsonResponse({
#                         'error': 'Repository not found. Please check the URL.',
#                         'detail': error_msg
#                     }, status=404)
#
#                 # Generic clone error
#                 return JsonResponse({'error': f'Git clone failed: {error_msg}'}, status=400)
#
#             # Determine the analysis path (subdirectory or full repo)
#             analysis_path = temp_path
#             if subdirectory:
#                 subdir_path = temp_path / subdirectory
#                 if not subdir_path.exists():
#                     shutil.rmtree(temp_path, ignore_errors=True)
#                     return JsonResponse({
#                         'error': f'Subdirectory "{subdirectory}" not found in repository'
#                     }, status=404)
#                 analysis_path = subdir_path
#
#             # Analyze file extensions
#             extensions = set()
#             file_count = 0
#
#             ignore_patterns = {'.git', 'node_modules', '__pycache__', 'dist', 'build', '.egg-info', 'htmlcov', 'venv', '.venv'}
#
#             for file_path in analysis_path.rglob('*'):
#                 if file_path.is_file():
#                     # Skip if in ignored directory
#                     if any(pattern in str(file_path) for pattern in ignore_patterns):
#                         continue
#
#                     ext = file_path.suffix.lower()
#                     if ext:
#                         extensions.add(ext)
#                     file_count += 1
#
#             # Store temp path and metadata for later use
#             session_key = str(temp_path)
#             _temp_repos[session_key] = {
#                 'temp_path': temp_path,
#                 'subdirectory': subdirectory,
#                 'branch': branch,
#             }
#
#             return JsonResponse({
#                 'success': True,
#                 'temp_path': session_key,
#                 'extensions': sorted(list(extensions)),
#                 'file_count': file_count,
#                 'subdirectory': subdirectory,
#                 'branch': branch or 'main',
#             })
#
#         except subprocess.TimeoutExpired:
#             shutil.rmtree(temp_path, ignore_errors=True)
#             return JsonResponse({'error': 'Clone timeout (>60s). Repository may be too large.'}, status=400)
#         except Exception as e:
#             shutil.rmtree(temp_path, ignore_errors=True)
#             logger.error(f'Error cloning repository: {e}')
#             return JsonResponse({'error': str(e)}, status=500)
#
#     except Exception as e:
#         logger.error(f'Error in clone_and_analyze: {e}')
#         return JsonResponse({'error': str(e)}, status=500)
#
#
# @require_http_methods(["POST"])
# def api_concatenate_repo(request):
#     """
#     Concatenate repository files and cleanup.
#
#     POST data:
#     - temp_path: Path to cloned repository
#     - max_lines: Maximum lines per file
#     - max_depth: Maximum directory depth
#     - extensions: List of file extensions to include
#
#     Returns:
#     - content: Concatenated markdown content
#     - stats: File count, line count, character count
#     """
#     try:
#         data = json.loads(request.body)
#         temp_path_key = data.get('temp_path', '')
#         max_lines = data.get('max_lines', 100)
#         max_depth = data.get('max_depth', 5)
#         extensions = set(data.get('extensions', []))
#
#         # Get temp path and metadata
#         repo_data = _temp_repos.get(temp_path_key)
#         if not repo_data:
#             return JsonResponse({'error': 'Repository not found or expired'}, status=404)
#
#         temp_path = repo_data['temp_path']
#         subdirectory = repo_data.get('subdirectory')
#         branch = repo_data.get('branch', 'main')
#
#         if not temp_path.exists():
#             return JsonResponse({'error': 'Repository path not found'}, status=404)
#
#         # Determine the base path for concatenation
#         base_path = temp_path
#         if subdirectory:
#             base_path = temp_path / subdirectory
#             if not base_path.exists():
#                 return JsonResponse({'error': f'Subdirectory "{subdirectory}" not found'}, status=404)
#
#         # Generate concatenated content
#         output = f'# Repository Contents: {subdirectory or "Root"}\n\n'
#         if subdirectory:
#             output += f'Branch: {branch}\nSubdirectory: {subdirectory}\n\n'
#
#         file_count = 0
#         line_count = 0
#         char_count = 0
#
#         ignore_patterns = {'.git', 'node_modules', '__pycache__', 'dist', 'build', '.egg-info', 'htmlcov', 'venv', '.venv'}
#
#         # Generate tree structure
#         output += '## Directory Structure\n```\n'
#         tree_lines = []
#         for file_path in sorted(base_path.rglob('*')):
#             if any(pattern in str(file_path) for pattern in ignore_patterns):
#                 continue
#
#             relative_path = file_path.relative_to(base_path)
#             depth = len(relative_path.parts) - 1
#
#             if depth <= max_depth:
#                 indent = '  ' * depth
#                 name = relative_path.name
#                 tree_lines.append(f'{indent}{name}')
#
#         output += '\n'.join(tree_lines[:500])  # Limit tree size
#         output += '\n```\n\n'
#
#         # Concatenate file contents
#         output += '## File Contents\n\n'
#
#         for file_path in sorted(base_path.rglob('*')):
#             if not file_path.is_file():
#                 continue
#
#             # Check ignore patterns
#             if any(pattern in str(file_path) for pattern in ignore_patterns):
#                 continue
#
#             # Check extension
#             ext = file_path.suffix.lower()
#             if ext not in extensions:
#                 continue
#
#             # Check depth
#             relative_path = file_path.relative_to(base_path)
#             depth = len(relative_path.parts) - 1
#             if depth > max_depth:
#                 continue
#
#             try:
#                 content = file_path.read_text(encoding='utf-8', errors='ignore')
#                 lines = content.splitlines()
#
#                 output += f'### {relative_path}\n```{ext[1:]}\n'
#
#                 if len(lines) <= max_lines:
#                     output += content
#                 else:
#                     output += '\n'.join(lines[:max_lines])
#                     output += f'\n... [{len(lines) - max_lines} lines truncated]'
#
#                 output += '\n```\n\n'
#
#                 file_count += 1
#                 line_count += min(len(lines), max_lines)
#                 char_count += len(content)
#
#             except Exception as e:
#                 logger.warning(f'Error reading {file_path}: {e}')
#                 continue
#
#         # Cleanup temporary directory
#         try:
#             shutil.rmtree(temp_path, ignore_errors=True)
#             del _temp_repos[temp_path_key]
#         except Exception as e:
#             logger.warning(f'Error cleaning up temp directory: {e}')
#
#         return JsonResponse({
#             'success': True,
#             'content': output,
#             'stats': {
#                 'file_count': file_count,
#                 'line_count': line_count,
#                 'char_count': char_count,
#             },
#         })
#
#     except Exception as e:
#         logger.error(f'Error in concatenate_repo: {e}')
#         return JsonResponse({'error': str(e)}, status=500)
#
#
# # EOF

# --------------------------------------------------------------------------------
# End of Source Code from: apps/public_app/tool_repo_concat_api.py
# --------------------------------------------------------------------------------
