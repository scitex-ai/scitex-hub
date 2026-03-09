from django.contrib import admin
from .models import (
    Project,
    ProjectMembership,
    ProjectPermission,
    # TODO: Uncomment when pull request models are available
    # PullRequest,
    # PullRequestReview,
    # PullRequestComment,
    # PullRequestCommit,
    # PullRequestLabel,
    # PullRequestEvent,
)

# Organization and ResearchGroup models now managed in organizations_app

# Organization and ResearchGroup admin now in organizations_app.admin


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "progress", "created_at", "updated_at")
    search_fields = ("name", "description", "owner__username")
    list_filter = ("created_at", "updated_at", "organization")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Basic Information", {"fields": ("name", "description", "owner", "progress")}),
        (
            "Organization",
            {"fields": ("organization", "research_group"), "classes": ("collapse",)},
        ),
        (
            "Research Data",
            {
                "fields": (
                    "hypotheses",
                    "source_code_url",
                    "data_location",
                    "manuscript_draft",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "GitHub Integration",
            {
                "fields": (
                    "github_integration_enabled",
                    "github_repo_name",
                    "github_owner",
                    "current_branch",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at", "last_activity"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "role", "permission_level", "joined_at")
    search_fields = ("project__name", "user__username")
    list_filter = ("role", "permission_level", "joined_at")


@admin.register(ProjectPermission)
class ProjectPermissionAdmin(admin.ModelAdmin):
    list_display = ("membership", "resource_type", "permission_level")
    search_fields = ("membership__project__name", "membership__user__username")
    list_filter = ("resource_type", "permission_level")


# Pull Request Admin
# TODO: Uncomment when pull request models are available
"""
@admin.register(PullRequest)
class PullRequestAdmin(admin.ModelAdmin):
    list_display = ('number', 'title', 'project', 'author', 'state', 'source_branch', 'target_branch', 'created_at')
    search_fields = ('title', 'description', 'project__name', 'author__username')
    list_filter = ('state', 'is_draft', 'has_conflicts', 'created_at')
    readonly_fields = ('number', 'created_at', 'updated_at', 'merged_at', 'closed_at')
    filter_horizontal = ('reviewers', 'assignees')
    fieldsets = (
        ('Basic Information', {
            'fields': ('project', 'number', 'title', 'description', 'author')
        }),
        ('Branches', {
            'fields': ('source_branch', 'target_branch')
        }),
        ('State', {
            'fields': ('state', 'is_draft', 'has_conflicts', 'conflict_files')
        }),
        ('Review', {
            'fields': ('reviewers', 'required_approvals', 'assignees')
        }),
        ('Labels & CI', {
            'fields': ('labels', 'ci_status')
        }),
        ('Merge Information', {
            'fields': ('merged_by', 'merge_commit_sha', 'merge_strategy', 'merged_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'closed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PullRequestReview)
class PullRequestReviewAdmin(admin.ModelAdmin):
    list_display = ('pull_request', 'reviewer', 'state', 'created_at')
    search_fields = ('pull_request__title', 'reviewer__username', 'content')
    list_filter = ('state', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(PullRequestComment)
class PullRequestCommentAdmin(admin.ModelAdmin):
    list_display = ('pull_request', 'author', 'file_path', 'line_number', 'created_at')
    search_fields = ('pull_request__title', 'author__username', 'content')
    list_filter = ('created_at', 'edited')
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('pull_request', 'author', 'parent_comment')


@admin.register(PullRequestCommit)
class PullRequestCommitAdmin(admin.ModelAdmin):
    list_display = ('commit_hash_short', 'pull_request', 'author_name', 'committed_at')
    search_fields = ('commit_hash', 'commit_message', 'author_name', 'author_email')
    list_filter = ('committed_at',)
    readonly_fields = ('created_at',)

    def commit_hash_short(self, obj):
        return obj.commit_hash[:7]
    commit_hash_short.short_description = 'Commit'


@admin.register(PullRequestLabel)
class PullRequestLabelAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'color', 'created_at')
    search_fields = ('name', 'description', 'project__name')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)


@admin.register(PullRequestEvent)
class PullRequestEventAdmin(admin.ModelAdmin):
    list_display = ('pull_request', 'event_type', 'actor', 'created_at')
    search_fields = ('pull_request__title', 'actor__username')
    list_filter = ('event_type', 'created_at')
    readonly_fields = ('created_at',)
"""
