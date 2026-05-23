#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_hub/_mcp_tools/gitea.py
"""Gitea CLI tools for FastMCP server."""

import json
import subprocess
from pathlib import Path
from typing import Optional


def _json(data: dict) -> str:
    return json.dumps(data, indent=2, default=str)


def _run_tea(*args) -> dict:
    """Execute tea command and return result."""
    tea_path = Path.home() / ".local" / "bin" / "tea"
    if not tea_path.exists():
        return {
            "success": False,
            "error": "tea CLI not found",
            "hint": "Install: wget https://dl.gitea.com/tea/0.9.2/tea-0.9.2-linux-amd64 "
            "-O ~/.local/bin/tea && chmod +x ~/.local/bin/tea",
        }
    try:
        result = subprocess.run(
            [str(tea_path)] + list(args),
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _run_git(*args) -> dict:
    """Execute git command and return result."""
    try:
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def register_gitea_tools(mcp) -> None:
    """Register Gitea CLI tools with FastMCP server."""

    @mcp.tool()
    async def repo_login(
        url: str = "http://localhost:3001",
        token: Optional[str] = None,
        name: str = "scitex",
    ) -> str:
        """Use when the user asks to authenticate with SciTeX Hub Gitea, add a tea login, or configure repo access; replaces manual `tea login add` commands and Gitea REST API auth setup."""
        args = ["login", "add", "--name", name, "--url", url]
        if token:
            args.extend(["--token", token])
        result = _run_tea(*args)
        return _json(result)

    @mcp.tool()
    async def repo_clone(
        repository: str,
        destination: Optional[str] = None,
        login: str = "scitex-dev",
    ) -> str:
        """Use when the user asks to clone a SciTeX Hub repo, check out a Gitea project, or download source; replaces manual `git clone`, `tea clone`, gh CLI, and Gitea REST API calls. Auto-resolves owner if repository is given bare."""
        if "/" not in repository:
            # Try to find owner
            list_result = _run_tea(
                "repos", "ls", "--login", login, "--fields", "name,owner"
            )
            if list_result["success"]:
                for line in list_result["stdout"].split("\n"):
                    if repository in line:
                        parts = line.split("|")
                        if len(parts) >= 2:
                            owner = parts[1].strip()
                            if owner and owner != "OWNER":
                                repository = f"{owner}/{repository}"
                                break
            if "/" not in repository:
                return _json(
                    {
                        "success": False,
                        "error": f"Repository '{repository}' not found",
                    }
                )

        args = ["clone", "--login", login, repository]
        if destination:
            args.append(destination)
        result = _run_tea(*args)
        return _json(result)

    @mcp.tool()
    async def repo_create(
        name: str,
        description: Optional[str] = None,
        private: bool = False,
        login: str = "scitex-dev",
    ) -> str:
        """Use when the user asks to create a new SciTeX Hub repository, make a Gitea repo, or start a new code project; replaces manual `tea repo create`, gh CLI, PyGithub, and Gitea REST API calls."""
        args = ["repo", "create", "--name", name, "--login", login]
        if description:
            args.extend(["--description", description])
        if private:
            args.append("--private")
        result = _run_tea(*args)
        return _json(result)

    @mcp.tool()
    async def repo_list(
        user: Optional[str] = None,
        login: str = "scitex-dev",
        starred: bool = False,
        watched: bool = False,
    ) -> str:
        """Use when the user asks to list their SciTeX Hub repositories, browse Gitea repos, see starred/watched projects; replaces manual `tea repos`, `gh repo list`, PyGithub, and Gitea REST API calls."""
        args = ["repos", "--login", login, "--output", "table"]
        if starred:
            args.append("--starred")
        if watched:
            args.append("--watched")
        if user:
            args.append(user)
        result = _run_tea(*args)
        return _json(result)

    @mcp.tool()
    async def repo_search(
        query: str,
        login: str = "scitex-dev",
        limit: int = 10,
    ) -> str:
        """Use when the user asks to search SciTeX Hub repositories, find a Gitea repo by keyword, or discover projects; replaces manual `tea repos search`, `gh search repos`, PyGithub, and Gitea REST API calls."""
        result = _run_tea(
            "repos", "search", "--login", login, "--limit", str(limit), query
        )
        return _json(result)

    @mcp.tool()
    async def repo_delete(
        repository: str,
        login: str = "scitex-dev",
        confirm: bool = False,
    ) -> str:
        """Use when the user asks to delete a SciTeX Hub repository or remove a Gitea repo; replaces manual Gitea REST API DELETE calls, `gh repo delete`, and PyGithub. DANGEROUS: requires confirm=True; repository must be in 'owner/repo' format."""
        if not confirm:
            return _json(
                {
                    "success": False,
                    "error": "Set confirm=True to delete",
                    "warning": "This action is irreversible!",
                }
            )

        if "/" not in repository:
            return _json(
                {
                    "success": False,
                    "error": "Repository must be in 'username/repo' format",
                }
            )

        import yaml

        config_path = Path.home() / ".config" / "tea" / "config.yml"
        if not config_path.exists():
            return _json({"success": False, "error": "Tea config not found"})

        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)

            login_config = None
            for l in config.get("logins", []):
                if l["name"] == login:
                    login_config = l
                    break

            if not login_config:
                return _json({"success": False, "error": f"Login '{login}' not found"})

            owner, repo = repository.split("/", 1)
            api_url = f"{login_config['url']}/api/v1/repos/{owner}/{repo}"
            headers = {"Authorization": f"token {login_config['token']}"}

            import requests

            response = requests.delete(api_url, headers=headers, timeout=30)

            if response.status_code == 204:
                return _json(
                    {"success": True, "message": f"Repository '{repository}' deleted"}
                )
            elif response.status_code == 404:
                return _json(
                    {"success": False, "error": f"Repository '{repository}' not found"}
                )
            else:
                return _json(
                    {
                        "success": False,
                        "error": f"Delete failed (status {response.status_code})",
                    }
                )
        except Exception as e:
            return _json({"success": False, "error": str(e)})

    @mcp.tool()
    async def repo_fork(repository: str) -> str:
        """Use when the user asks to fork a SciTeX Hub repository or copy a Gitea repo to their account; replaces manual `tea repo fork`, `gh repo fork`, PyGithub, and Gitea REST API calls."""
        result = _run_tea("repo", "fork", repository)
        return _json(result)

    @mcp.tool()
    async def repo_pr_create(
        title: Optional[str] = None,
        description: Optional[str] = None,
        base: str = "main",
        head: Optional[str] = None,
    ) -> str:
        """Use when the user asks to open a pull request, create a PR on SciTeX Hub, or request a merge in Gitea; replaces manual `tea pr create`, `gh pr create`, PyGithub, and Gitea REST API calls."""
        args = ["pr", "create"]
        if title:
            args.extend(["--title", title])
        if description:
            args.extend(["--description", description])
        if base:
            args.extend(["--base", base])
        if head:
            args.extend(["--head", head])
        result = _run_tea(*args)
        return _json(result)

    @mcp.tool()
    async def repo_pr_list() -> str:
        """Use when the user asks to list PRs, see open pull requests, or review merge requests on SciTeX Hub; replaces manual `tea pr list`, `gh pr list`, PyGithub, and Gitea REST API calls for the current repository."""
        result = _run_tea("pr", "list")
        return _json(result)

    @mcp.tool()
    async def repo_issue_create(
        title: str,
        body: Optional[str] = None,
    ) -> str:
        """Use when the user asks to file an issue, report a bug, or open a ticket on SciTeX Hub; replaces manual `tea issue create`, `gh issue create`, PyGithub, and Gitea REST API calls."""
        args = ["issue", "create", "--title", title]
        if body:
            args.extend(["--body", body])
        result = _run_tea(*args)
        return _json(result)

    @mcp.tool()
    async def repo_issue_list() -> str:
        """Use when the user asks to list issues, see open bugs/tickets, or review issues on SciTeX Hub; replaces manual `tea issue list`, `gh issue list`, PyGithub, and Gitea REST API calls for the current repository."""
        result = _run_tea("issue", "list")
        return _json(result)

    @mcp.tool()
    async def repo_push() -> str:
        """Use when the user asks to push commits, upload changes, or sync local work to SciTeX Hub; replaces manual `git push origin <branch>`, `gh` pushes, and Gitea REST API sync (pushes current branch to origin)."""
        branch_result = _run_git("branch", "--show-current")
        if not branch_result["success"]:
            return _json({"success": False, "error": "Not in a git repository"})

        branch = branch_result["stdout"].strip()
        if not branch:
            return _json({"success": False, "error": "Not on any branch"})

        result = _run_git("push", "origin", branch)
        if result["success"]:
            result["message"] = f"Pushed to origin/{branch}"
        return _json(result)

    @mcp.tool()
    async def repo_pull() -> str:
        """Use when the user asks to pull changes, fetch updates, or sync from SciTeX Hub; replaces manual `git pull origin <branch>` and Gitea REST API sync (pulls current branch from origin)."""
        branch_result = _run_git("branch", "--show-current")
        if not branch_result["success"]:
            return _json({"success": False, "error": "Not in a git repository"})

        branch = branch_result["stdout"].strip()
        if not branch:
            return _json({"success": False, "error": "Not on any branch"})

        result = _run_git("pull", "origin", branch)
        if result["success"]:
            result["message"] = f"Pulled from origin/{branch}"
        return _json(result)

    @mcp.tool()
    async def repo_status() -> str:
        """Use when the user asks about git status, modified files, staged changes, or working tree state in a SciTeX Hub-cloned repo; replaces manual `git status` shell invocations."""
        result = _run_git("status")
        return _json(result)


# EOF
