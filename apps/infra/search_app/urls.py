from django.urls import path
from . import views

app_name = "search_app"

urlpatterns = [
    # Main search page
    path("", views.unified_search, name="search"),
    # Autocomplete API
    path("api/autocomplete/", views.autocomplete, name="autocomplete"),
    # Search stats
    path("api/stats/", views.search_stats, name="stats"),
]
