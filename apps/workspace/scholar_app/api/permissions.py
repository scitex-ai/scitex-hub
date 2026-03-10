#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Permissions for Scholar App

This module defines custom permission classes for API endpoints.
"""

from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Permission to check if user is the owner of the object
    """

    def has_object_permission(self, request, view, obj):
        """Check if user owns the object"""
        return obj.user == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission to allow owners to edit their objects,
    otherwise read-only access
    """

    def has_object_permission(self, request, view, obj):
        """Check if user owns the object or request is read-only"""
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class CanAccessPaper(permissions.BasePermission):
    """
    Permission to check if user can access a paper
    (through their collections or shared access)
    """

    def has_object_permission(self, request, view, obj):
        """Check if user can access the paper"""
        # Check if paper is in any of user's collections
        user_collections = obj.collections.filter(user=request.user)
        return user_collections.exists()


class CanAccessCollection(permissions.BasePermission):
    """
    Permission to check if user can access a collection
    """

    def has_object_permission(self, request, view, obj):
        """Check if user owns or has access to the collection"""
        return obj.user == request.user


class CanAccessAnnotation(permissions.BasePermission):
    """
    Permission to check if user can access an annotation
    """

    def has_object_permission(self, request, view, obj):
        """Check if user can access the annotation"""
        # User can access if they own the annotation or
        # they have access to the paper through collections
        if obj.user == request.user:
            return True

        # Check if user has access to the paper
        user_collections = obj.paper.collections.filter(user=request.user)
        return user_collections.exists()


# EOF
