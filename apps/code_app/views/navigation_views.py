"""
Basic navigation and landing page views.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages


@login_required
def index(request):
    """Code app - redirect to user's projects."""
    messages.info(request, "Please select or create a project to use Code.")
    return redirect("user_projects:user_projects", username=request.user.username)


def features(request):
    """Code features view."""
    return render(request, "code_app/features.html")


def pricing(request):
    """Code pricing view."""
    return render(request, "code_app/pricing.html")


@login_required
def editor(request):
    """SciTeX Code editor interface."""
    from ..models import CodeExecutionJob, Notebook

    # Get user's recent jobs for sidebar
    recent_jobs = CodeExecutionJob.objects.filter(user=request.user)[:5]

    context = {
        "recent_jobs": recent_jobs,
        "user_notebooks": Notebook.objects.filter(user=request.user)[:5],
    }
    return render(request, "code_app/editor.html", context)
