"""
Citation Graph API URL Configuration

Routes for /api/scholar/citation-graph/ endpoints.
"""

from django.urls import path
from . import citation_graph

app_name = "citation_graph_api"

urlpatterns = [
    # Network Analysis
    path("network/", citation_graph.build_network, name="network"),
    path("related/", citation_graph.get_related_papers, name="related"),
    path("paper/", citation_graph.paper_summary, name="paper"),
    path("health/", citation_graph.health, name="health"),
]

# EOF
