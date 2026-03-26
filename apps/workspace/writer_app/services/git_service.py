"""
Git Service for Writer Operations
Provides visual Git interface for non-technical users:
- Auto-commit on save
- Commit history visualization
- Diff display
- Branch management
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import git
from git import Actor, GitCommandError, Repo

logger = logging.getLogger(__name__)


class GitService:
    """Git operations for writer manuscripts with user-friendly interface."""

    def __init__(
        self,
        writer_dir: Path,
        user_name: str = "SciTeX Writer",
        user_email: str = "writer@scitex.app",
    ):
        """
        Initialize Git service for a writer directory.

        Args:
            writer_dir: Path to writer directory (scitex/writer/)
            user_name: Git author name
            user_email: Git author email
        """
        self.writer_dir = Path(writer_dir)
        self.user_name = user_name
        self.user_email = user_email
        self.repo: Optional[Repo] = None

        # Initialize or load repository
        self._init_or_load_repo()

    def _init_or_load_repo(self) -> None:
        """Initialize new Git repo or load existing one."""
        try:
            # Try to load existing repo
            self.repo = Repo(self.writer_dir)
            logger.info(f"[Git] Loaded existing repository at {self.writer_dir}")
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            # Initialize new repository
            self.repo = Repo.init(self.writer_dir)
            logger.info(f"[Git] Initialized new repository at {self.writer_dir}")

            # Configure user
            with self.repo.config_writer() as config:
                config.set_value("user", "name", self.user_name)
                config.set_value("user", "email", self.user_email)

            # Create .gitignore
            self._create_gitignore()

            # Initial commit
            self.commit("Initial commit", auto_stage=True)

    def _create_gitignore(self) -> None:
        """Create .gitignore file for writer directory."""
        gitignore_content = """# Compiled PDFs (temporary)
.preview/
*.aux
*.log
*.out
*.toc
*.synctex.gz
*.fls
*.fdb_latexmk

# System files
.DS_Store
Thumbs.db
*.swp
*.swo
*~

# IDE
.vscode/
.idea/
*.code-workspace
"""
        gitignore_path = self.writer_dir / ".gitignore"
        gitignore_path.write_text(gitignore_content)
        logger.info("[Git] Created .gitignore")

    def commit(
        self,
        message: str,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None,
        auto_stage: bool = True,
    ) -> Optional[str]:
        """
        Create a commit with user-friendly message.

        Args:
            message: Commit message
            author_name: Override author name
            author_email: Override author email
            auto_stage: Automatically stage all changes

        Returns:
            Commit SHA if successful, None otherwise
        """
        if not self.repo:
            logger.error("[Git] Repository not initialized")
            return None

        try:
            # Stage changes
            if auto_stage:
                self.repo.git.add(A=True)  # Add all files
                logger.info("[Git] Staged all changes")

            # Check if there are changes to commit
            if not self.repo.is_dirty() and not self.repo.untracked_files:
                logger.info("[Git] No changes to commit")
                return None

            # Create author
            author = Actor(
                author_name or self.user_name, author_email or self.user_email
            )

            # Commit
            commit = self.repo.index.commit(message, author=author, committer=author)
            logger.info(f"[Git] Created commit {commit.hexsha[:8]}: {message}")

            return commit.hexsha

        except GitCommandError as e:
            logger.error(f"[Git] Failed to commit: {e}")
            return None

    def get_commit_history(
        self, max_count: int = 50, branch: str = "HEAD"
    ) -> List[Dict]:
        """
        Get commit history for visualization.

        Args:
            max_count: Maximum number of commits to retrieve
            branch: Branch name (default: current branch)

        Returns:
            List of commit dictionaries with user-friendly info
        """
        if not self.repo:
            return []

        try:
            commits = []
            for commit in self.repo.iter_commits(branch, max_count=max_count):
                commits.append(
                    {
                        "sha": commit.hexsha,
                        "sha_short": commit.hexsha[:8],
                        "message": commit.message.strip(),
                        "author_name": commit.author.name,
                        "author_email": commit.author.email,
                        "date": datetime.fromtimestamp(commit.committed_date),
                        "date_relative": self._get_relative_time(commit.committed_date),
                        "parent_shas": [p.hexsha for p in commit.parents],
                        "stats": {
                            "files_changed": len(commit.stats.files),
                            "insertions": commit.stats.total["insertions"],
                            "deletions": commit.stats.total["deletions"],
                        },
                    }
                )

            logger.info(f"[Git] Retrieved {len(commits)} commits")
            return commits

        except GitCommandError as e:
            logger.error(f"[Git] Failed to get history: {e}")
            return []

    def get_diff(
        self, commit_sha: Optional[str] = None, compare_to: Optional[str] = None
    ) -> Dict:
        """
        Get diff for visualization.

        Args:
            commit_sha: Commit to show diff for (default: working directory)
            compare_to: Commit to compare against (default: previous commit)

        Returns:
            Dictionary with diff information
        """
        if not self.repo:
            return {"files": [], "stats": {"files": 0, "insertions": 0, "deletions": 0}}

        try:
            if commit_sha:
                # Diff for specific commit
                commit = self.repo.commit(commit_sha)
                if compare_to:
                    diff_index = commit.diff(compare_to)
                else:
                    # Diff against parent
                    if commit.parents:
                        diff_index = commit.diff(commit.parents[0])
                    else:
                        # Initial commit
                        diff_index = commit.diff(git.NULL_TREE)
            else:
                # Diff for working directory
                diff_index = self.repo.head.commit.diff(None)

            files = []
            total_insertions = 0
            total_deletions = 0

            for diff_item in diff_index:
                # Get file path
                file_path = diff_item.a_path or diff_item.b_path

                # Get change type
                if diff_item.new_file:
                    change_type = "added"
                elif diff_item.deleted_file:
                    change_type = "deleted"
                elif diff_item.renamed_file:
                    change_type = "renamed"
                else:
                    change_type = "modified"

                # Get diff content
                try:
                    diff_text = diff_item.diff.decode("utf-8", errors="replace")
                except AttributeError:
                    diff_text = ""

                # Count insertions/deletions
                insertions = diff_text.count("\n+") - 1  # -1 for header
                deletions = diff_text.count("\n-") - 1

                # Retrieve original and modified file contents for Monaco DiffEditor
                original_content = ""
                modified_content = ""
                try:
                    if diff_item.a_blob:
                        original_content = diff_item.a_blob.data_stream.read().decode(
                            "utf-8", errors="replace"
                        )
                    if diff_item.b_blob:
                        modified_content = diff_item.b_blob.data_stream.read().decode(
                            "utf-8", errors="replace"
                        )
                except Exception as blob_err:
                    logger.debug(f"[Git] Could not read blob content: {blob_err}")

                files.append(
                    {
                        "path": file_path,
                        "change_type": change_type,
                        "diff": diff_text,
                        "insertions": insertions,
                        "deletions": deletions,
                        "original_content": original_content,
                        "modified_content": modified_content,
                    }
                )

                total_insertions += insertions
                total_deletions += deletions

            return {
                "files": files,
                "stats": {
                    "files": len(files),
                    "insertions": total_insertions,
                    "deletions": total_deletions,
                },
            }

        except (GitCommandError, ValueError) as e:
            logger.error(f"[Git] Failed to get diff: {e}")
            return {"files": [], "stats": {"files": 0, "insertions": 0, "deletions": 0}}

    def get_branches(self) -> List[Dict]:
        """
        Get list of branches for visualization.

        Returns:
            List of branch dictionaries
        """
        if not self.repo:
            return []

        try:
            branches = []
            for branch in self.repo.branches:
                is_current = branch == self.repo.active_branch

                branches.append(
                    {
                        "name": branch.name,
                        "is_current": is_current,
                        "commit_sha": branch.commit.hexsha,
                        "commit_sha_short": branch.commit.hexsha[:8],
                        "commit_message": branch.commit.message.strip(),
                        "last_commit_date": datetime.fromtimestamp(
                            branch.commit.committed_date
                        ),
                    }
                )

            return branches

        except GitCommandError as e:
            logger.error(f"[Git] Failed to get branches: {e}")
            return []

    def create_branch(
        self, branch_name: str, from_commit: Optional[str] = None
    ) -> bool:
        """
        Create a new branch.

        Args:
            branch_name: Name of new branch
            from_commit: Commit to branch from (default: current HEAD)

        Returns:
            True if successful
        """
        if not self.repo:
            return False

        try:
            if from_commit:
                start_point = self.repo.commit(from_commit)
                self.repo.create_head(branch_name, start_point)
            else:
                self.repo.create_head(branch_name)

            logger.info(f"[Git] Created branch '{branch_name}'")
            return True

        except GitCommandError as e:
            logger.error(f"[Git] Failed to create branch: {e}")
            return False

    def switch_branch(self, branch_name: str) -> bool:
        """
        Switch to a different branch.

        Args:
            branch_name: Name of branch to switch to

        Returns:
            True if successful
        """
        if not self.repo:
            return False

        try:
            # Check for uncommitted changes
            if self.repo.is_dirty():
                logger.warning("[Git] Working directory has uncommitted changes")
                return False

            # Switch branch
            self.repo.git.checkout(branch_name)
            logger.info(f"[Git] Switched to branch '{branch_name}'")
            return True

        except GitCommandError as e:
            logger.error(f"[Git] Failed to switch branch: {e}")
            return False

    def get_status(self) -> Dict:
        """
        Get current repository status.

        Returns:
            Dictionary with status information
        """
        if not self.repo:
            return {"clean": True, "files": []}

        try:
            status = {
                "branch": self.repo.active_branch.name,
                "clean": not self.repo.is_dirty(),
                "files": {
                    "modified": [item.a_path for item in self.repo.index.diff(None)],
                    "staged": [item.a_path for item in self.repo.index.diff("HEAD")],
                    "untracked": self.repo.untracked_files,
                },
            }
            return status

        except GitCommandError as e:
            logger.error(f"[Git] Failed to get status: {e}")
            return {"clean": True, "files": []}

    def _get_relative_time(self, timestamp: int) -> str:
        """Convert timestamp to relative time string."""
        now = datetime.now()
        commit_time = datetime.fromtimestamp(timestamp)
        delta = now - commit_time

        if delta.days > 365:
            years = delta.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
        elif delta.days > 30:
            months = delta.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        elif delta.days > 0:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "just now"
