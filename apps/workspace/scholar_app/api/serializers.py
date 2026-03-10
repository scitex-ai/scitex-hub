#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DRF Serializers for Scholar App API

This module contains serializers for API endpoints.
"""

from rest_framework import serializers
from ..models import (
    SearchIndex as Paper,
    Collection,
    SavedSearch,
    Annotation,
    AnnotationVote,
    RepositoryConnection,
    Dataset,
)


class PaperSerializer(serializers.ModelSerializer):
    """Serializer for SearchIndex (Paper) model"""

    class Meta:
        model = Paper
        fields = [
            "id",
            "title",
            "abstract",
            "doi",
            "pmid",
            "arxiv_id",
            "document_type",
            "publication_date",
            "authors",
            "journal",
            "external_url",
            "pdf_url",
            "bibtex_content",
            "keywords",
            "citation_count",
            "view_count",
            "download_count",
            "is_open_access",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CollectionSerializer(serializers.ModelSerializer):
    """Serializer for Collection model"""

    class Meta:
        model = Collection
        fields = ["id", "name", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SavedSearchSerializer(serializers.ModelSerializer):
    """Serializer for SavedSearch model"""

    class Meta:
        model = SavedSearch
        fields = ["id", "name", "query", "filters", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AnnotationVoteSerializer(serializers.ModelSerializer):
    """Serializer for AnnotationVote model"""

    class Meta:
        model = AnnotationVote
        fields = ["id", "annotation", "user", "vote_type"]


class AnnotationSerializer(serializers.ModelSerializer):
    """Serializer for Annotation model"""

    votes = AnnotationVoteSerializer(many=True, read_only=True)

    class Meta:
        model = Annotation
        fields = ["id", "paper", "user", "text", "tag", "created_at", "votes"]
        read_only_fields = ["id", "created_at", "votes"]


class RepositoryConnectionSerializer(serializers.ModelSerializer):
    """Serializer for RepositoryConnection model"""

    class Meta:
        model = RepositoryConnection
        fields = ["id", "name", "platform", "credentials", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class DatasetMetadataSerializer(serializers.ModelSerializer):
    """Serializer for Dataset metadata"""

    class Meta:
        model = Dataset
        fields = ["id", "title", "description", "owner", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


# EOF
