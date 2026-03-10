#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: ./apps/public_app/management/commands/sync_github_contributors.py

import json
import subprocess

from django.core.management.base import BaseCommand

from apps.infra.public_app.models import Contributor


class Command(BaseCommand):
    help = "Sync contributors from GitHub repository"

    def add_arguments(self, parser):
        parser.add_argument(
            "--repo",
            type=str,
            default="ywatanabe1989/scitex-cloud",
            help="GitHub repository (owner/repo format)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be synced without saving to database",
        )

    def handle(self, *args, **options):
        repo = options["repo"]
        dry_run = options["dry_run"]

        self.stdout.write(f"Syncing contributors from GitHub repo: {repo}")

        try:
            # Fetch contributors from GitHub using gh CLI
            result = subprocess.run(
                ["gh", "api", f"repos/{repo}/contributors", "--paginate"],
                capture_output=True,
                text=True,
                check=True,
            )

            contributors_data = json.loads(result.stdout)

            if not contributors_data:
                self.stdout.write(self.style.WARNING("No contributors found"))
                return

            created_count = 0
            updated_count = 0
            skipped_count = 0

            for contributor in contributors_data:
                username = contributor.get("login")
                contributions = contributor.get("contributions", 0)

                if not username:
                    skipped_count += 1
                    continue

                # Get additional user info
                try:
                    user_result = subprocess.run(
                        ["gh", "api", f"users/{username}"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    user_data = json.loads(user_result.stdout)
                    name = user_data.get("name") or username
                except:
                    name = username

                # Prepare contributor data
                contributor_data = {
                    "name": name,
                    "avatar_url": contributor.get("avatar_url", ""),
                    "github_url": contributor.get("html_url", ""),
                    "contributions": contributions,
                }

                # Determine role based on contributions or username
                if username == "ywatanabe1989":
                    contributor_data["role"] = "creator"
                    contributor_data["is_core_team"] = True
                    contributor_data["display_order"] = 1
                    contributor_data["contributions_description"] = (
                        "Architecture, Core Development, Research"
                    )
                elif contributions >= 100:
                    contributor_data["role"] = "core"
                    contributor_data["is_core_team"] = True
                    contributor_data["display_order"] = 10
                elif contributions >= 50:
                    contributor_data["role"] = "maintainer"
                    contributor_data["is_core_team"] = False
                    contributor_data["display_order"] = 100
                else:
                    contributor_data["role"] = "contributor"
                    contributor_data["is_core_team"] = False
                    contributor_data["display_order"] = 1000

                # Update or create contributor
                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[DRY RUN] Would sync: {username} "
                            f"({contributions} contributions, role: {contributor_data['role']})"
                        )
                    )
                    created_count += 1
                else:
                    obj, created = Contributor.objects.update_or_create(
                        github_username=username,
                        defaults=contributor_data,
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Created contributor: {username} "
                                f"({contributions} contributions)"
                            )
                        )
                    else:
                        updated_count += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"Updated contributor: {username} "
                                f"({contributions} contributions)"
                            )
                        )

            # Summary
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n[DRY RUN] Would sync {created_count} contributors"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nSuccessfully synced {created_count + updated_count} contributors "
                        f"({created_count} created, {updated_count} updated, "
                        f"{skipped_count} skipped)"
                    )
                )

                # Show core team
                core_team = Contributor.objects.filter(is_core_team=True)
                if core_team.exists():
                    self.stdout.write("\nCore Team Members:")
                    for member in core_team:
                        self.stdout.write(
                            f"  - {member.name} (@{member.github_username}): "
                            f"{member.contributions} contributions"
                        )

        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f"Error fetching contributors from GitHub: {e.stderr}")
            )
            self.stdout.write(
                self.style.WARNING(
                    "Make sure 'gh' CLI is installed and authenticated: "
                    "https://cli.github.com/"
                )
            )
        except json.JSONDecodeError as e:
            self.stdout.write(
                self.style.ERROR(f"Error parsing GitHub API response: {str(e)}")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Unexpected error: {str(e)}"))
