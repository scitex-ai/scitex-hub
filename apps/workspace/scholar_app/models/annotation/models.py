from django.db import models
from django.contrib.auth.models import User
import uuid


class Annotation(models.Model):
    """User annotations on research papers"""

    ANNOTATION_TYPE_CHOICES = [
        ("highlight", "Text Highlight"),
        ("note", "Margin Note"),
        ("comment", "General Comment"),
        ("question", "Question"),
        ("important", "Important Point"),
        ("critique", "Critical Analysis"),
        ("summary", "Summary"),
        ("methodology", "Methodology Note"),
    ]

    PRIVACY_CHOICES = [
        ("private", "Private (Only Me)"),
        ("shared", "Shared with Collaborators"),
        ("public", "Public (Anyone can view)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="annotations")
    paper = models.ForeignKey(
        "SearchIndex", on_delete=models.CASCADE, related_name="annotations"
    )

    # Annotation content
    annotation_type = models.CharField(
        max_length=20, choices=ANNOTATION_TYPE_CHOICES, default="note"
    )
    text_content = models.TextField(help_text="The annotation text/note content")
    highlighted_text = models.TextField(
        blank=True, help_text="The text that was highlighted (if applicable)"
    )

    # Position information (for PDF/document positioning)
    page_number = models.IntegerField(
        null=True, blank=True, help_text="Page number in document"
    )
    position_data = models.JSONField(
        default=dict, blank=True, help_text="JSON data for precise positioning"
    )

    # Collaboration and sharing
    privacy_level = models.CharField(
        max_length=10, choices=PRIVACY_CHOICES, default="private"
    )
    shared_with = models.ManyToManyField(
        User, blank=True, related_name="shared_annotations"
    )
    tags = models.ManyToManyField(
        "AnnotationTag", blank=True, related_name="annotations"
    )

    # Metadata
    is_resolved = models.BooleanField(
        default=False, help_text="For questions/issues - mark as resolved"
    )
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["paper", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["annotation_type"]),
            models.Index(fields=["privacy_level"]),
        ]

    def __str__(self):
        return (
            f"{self.user.username} - {self.annotation_type} on {self.paper.title[:50]}"
        )

    def get_vote_score(self):
        """Calculate net vote score"""
        return self.upvotes - self.downvotes


class AnnotationReply(models.Model):
    """Replies/responses to annotations for collaborative discussion"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    annotation = models.ForeignKey(
        Annotation, on_delete=models.CASCADE, related_name="replies"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="annotation_replies"
    )
    parent_reply = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="nested_replies",
    )

    content = models.TextField(help_text="Reply content")
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["annotation", "created_at"]),
        ]

    def __str__(self):
        return f"Reply by {self.user.username} to annotation {self.annotation.id}"

    def get_vote_score(self):
        """Calculate net vote score"""
        return self.upvotes - self.downvotes


class AnnotationVote(models.Model):
    """Track user votes on annotations and replies"""

    VOTE_CHOICES = [
        ("up", "Upvote"),
        ("down", "Downvote"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="annotation_votes"
    )
    annotation = models.ForeignKey(
        Annotation,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    reply = models.ForeignKey(
        AnnotationReply,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    vote_type = models.CharField(max_length=5, choices=VOTE_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Ensure one vote per user per annotation/reply
        constraints = [
            models.UniqueConstraint(
                fields=["user", "annotation"],
                condition=models.Q(annotation__isnull=False),
                name="unique_user_annotation_vote",
            ),
            models.UniqueConstraint(
                fields=["user", "reply"],
                condition=models.Q(reply__isnull=False),
                name="unique_user_reply_vote",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "annotation"]),
            models.Index(fields=["user", "reply"]),
        ]

    def __str__(self):
        target = self.annotation or self.reply
        return f"{self.user.username} {self.vote_type}voted {target}"


class AnnotationTag(models.Model):
    """Tags for organizing and categorizing annotations"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(
        max_length=7, default="#1a2332", help_text="Hex color code"
    )
    description = models.TextField(blank=True)

    # Usage tracking
    usage_count = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["-usage_count"]),
        ]

    def __str__(self):
        return self.name


# Research Data Repository Models


class CollaborationGroup(models.Model):
    """Groups for collaborative annotation sharing"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_groups"
    )
    members = models.ManyToManyField(
        User, through="GroupMembership", related_name="collaboration_groups"
    )

    # Group settings
    is_public = models.BooleanField(default=False, help_text="Allow anyone to join")
    auto_approve_members = models.BooleanField(
        default=True, help_text="Auto-approve membership requests"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["owner"]),
            models.Index(fields=["is_public"]),
        ]

    def __str__(self):
        return f"Group: {self.name} (owned by {self.owner.username})"

    def member_count(self):
        """Get total number of members"""
        return self.members.count()


class GroupMembership(models.Model):
    """Through model for CollaborationGroup membership with roles"""

    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Administrator"),
        ("editor", "Editor"),
        ("viewer", "Viewer"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("invited", "Invited"),
        ("requested", "Requested"),
        ("suspended", "Suspended"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(CollaborationGroup, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="viewer")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")

    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "group"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["group", "role"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.role} in {self.group.name}"
