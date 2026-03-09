from django.urls import path
from . import views

app_name = "social_app"

urlpatterns = [
    # Explore page
    path("explore/", views.explore, name="explore"),
    # Notifications
    path("notifications/", views.notifications, name="notifications"),
    # Follow/Unfollow APIs
    path("api/follow/<str:username>/", views.follow_user, name="follow"),
    path("api/unfollow/<str:username>/", views.unfollow_user, name="unfollow"),
    path("api/followers/<str:username>/", views.followers_list, name="followers_list"),
    path("api/following/<str:username>/", views.following_list, name="following_list"),
    # Star/Unstar APIs
    path("api/star/<str:username>/<slug:slug>/", views.star_repository, name="star"),
    path(
        "api/unstar/<str:username>/<slug:slug>/", views.unstar_repository, name="unstar"
    ),
    path(
        "api/stargazers/<str:username>/<slug:slug>/",
        views.stargazers_list,
        name="stargazers_list",
    ),
]
