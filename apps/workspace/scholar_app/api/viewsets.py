#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DRF ViewSets for Scholar App API

This module contains API viewsets for REST endpoints.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
import logging

from ..models import (
    SearchIndex as Paper,
    Collection,
    SavedSearch,
    Annotation,
)
from .serializers import (
    PaperSerializer,
    CollectionSerializer,
    SavedSearchSerializer,
    AnnotationSerializer,
)

logger = logging.getLogger(__name__)


class PaperViewSet(viewsets.ModelViewSet):
    """ViewSet for Paper/SearchIndex management"""

    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return papers from user's library"""
        user = self.request.user
        return Paper.objects.filter(userlibrary__user=user).distinct()

    @action(detail=False, methods=["post"])
    def save_paper(self, request):
        """Save a paper to user's library"""
        try:
            data = request.data
            doi = data.get("doi")
            title = data.get("title")
            external_url = data.get("external_url")

            paper, created = Paper.objects.get_or_create(
                doi=doi,
                defaults={
                    "title": title,
                    "external_url": external_url,
                },
            )

            serializer = self.get_serializer(paper)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error saving paper: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CollectionViewSet(viewsets.ModelViewSet):
    """ViewSet for Collection management"""

    serializer_class = CollectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return collections belonging to the user"""
        return Collection.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Create collection with current user"""
        serializer.save(user=self.request.user)


class SavedSearchViewSet(viewsets.ModelViewSet):
    """ViewSet for SavedSearch management"""

    serializer_class = SavedSearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return saved searches belonging to the user"""
        return SavedSearch.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Create saved search with current user"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        """Run a saved search"""
        saved_search = self.get_object()
        try:
            results = saved_search.execute_search()
            return Response(
                {
                    "count": len(results),
                    "results": results[:10],  # Return first 10 results
                }
            )
        except Exception as e:
            logger.error(f"Error running saved search: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AnnotationViewSet(viewsets.ModelViewSet):
    """ViewSet for Annotation management"""

    serializer_class = AnnotationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return annotations accessible to the user"""
        user = self.request.user
        return Annotation.objects.filter(user=user).distinct()

    def perform_create(self, serializer):
        """Create annotation with current user"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def vote(self, request, pk=None):
        """Vote on an annotation"""
        annotation = self.get_object()
        vote_type = request.data.get("vote_type")  # 'up' or 'down'

        try:
            vote, created = annotation.votes.get_or_create(
                user=request.user, defaults={"vote_type": vote_type}
            )
            if not created:
                vote.vote_type = vote_type
                vote.save()

            return Response({"success": True})
        except Exception as e:
            logger.error(f"Error voting on annotation: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# EOF
