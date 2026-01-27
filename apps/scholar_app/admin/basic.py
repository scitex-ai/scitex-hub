#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scholar app admin - Basic models (Author, Journal, Topic, etc.)."""

from __future__ import annotations

from django.contrib import admin

from ..models import Author, Collection, Journal, SearchIndex, Topic, UserLibrary


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = [
        "last_name",
        "first_name",
        "orcid",
        "affiliation",
        "h_index",
        "total_citations",
    ]
    list_filter = ["created_at", "h_index"]
    search_fields = ["first_name", "last_name", "orcid", "email", "affiliation"]
    ordering = ["last_name", "first_name"]


@admin.register(Journal)
class JournalAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "abbreviation",
        "issn",
        "publisher",
        "impact_factor",
        "open_access",
    ]
    list_filter = ["open_access", "publisher", "impact_factor"]
    search_fields = ["name", "abbreviation", "issn", "publisher"]


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "paper_count"]
    list_filter = ["parent"]
    search_fields = ["name", "description"]


@admin.register(SearchIndex)
class SearchIndexAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "document_type",
        "publication_date",
        "citation_count",
        "view_count",
        "status",
    ]
    list_filter = [
        "document_type",
        "status",
        "source",
        "is_open_access",
        "publication_date",
    ]
    search_fields = ["title", "abstract", "doi", "pmid", "arxiv_id"]
    date_hierarchy = "publication_date"
    ordering = ["-publication_date"]


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "is_public", "paper_count_display", "created_at"]
    list_filter = ["is_public", "created_at"]
    search_fields = ["name", "description", "user__username"]

    def paper_count_display(self, obj):
        return obj.paper_count()

    paper_count_display.short_description = "Paper Count"


@admin.register(UserLibrary)
class UserLibraryAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "paper_title",
        "reading_status",
        "importance_rating",
        "saved_at",
    ]
    list_filter = ["reading_status", "importance_rating", "saved_at"]
    search_fields = ["user__username", "paper__title", "project", "tags"]

    def paper_title(self, obj):
        title = obj.paper.title
        return title[:50] + "..." if len(title) > 50 else title

    paper_title.short_description = "Paper"


# EOF
