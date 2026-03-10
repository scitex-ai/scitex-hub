from django.urls import path

from apps.infra.platform_app.views.api import datastore as datastore_views
from apps.infra.platform_app.views.api import external_api as external_api_views
from apps.infra.platform_app.views.api import filevault as filevault_views
from apps.infra.platform_app.views.api import jobqueue as jobqueue_views
from apps.infra.platform_app.views.api import scitex_bridge as scitex_bridge_views

app_name = "platform_api"

urlpatterns = [
    # DataStore
    path(
        "data/<str:app>/<str:schema>/",
        datastore_views.datastore_list_create,
        name="datastore_list_create",
    ),
    path(
        "data/<str:app>/<str:schema>/<uuid:pk>/",
        datastore_views.datastore_detail,
        name="datastore_detail",
    ),
    path(
        "data/<str:app>/<str:schema>/search/",
        datastore_views.datastore_search,
        name="datastore_search",
    ),
    # FileVault
    path(
        "files/<str:app>/",
        filevault_views.filevault_root,
        name="filevault_root",
    ),
    path(
        "files/<str:app>/<path:file_path>",
        filevault_views.filevault_file,
        name="filevault_file",
    ),
    # JobQueue
    path(
        "jobs/<str:app>/submit/",
        jobqueue_views.job_submit,
        name="job_submit",
    ),
    path(
        "jobs/<str:app>/<uuid:job_id>/",
        jobqueue_views.job_detail,
        name="job_detail",
    ),
    path(
        "jobs/<str:app>/<uuid:job_id>/cancel/",
        jobqueue_views.job_cancel,
        name="job_cancel",
    ),
    path(
        "jobs/<str:app>/",
        jobqueue_views.job_list,
        name="job_list",
    ),
    # scitex Bridge
    path(
        "scitex/<str:module>/<str:function>/",
        scitex_bridge_views.scitex_call,
        name="scitex_call",
    ),
    # ExternalAPI
    path(
        "external/<str:api_name>/",
        external_api_views.external_proxy,
        name="external_proxy",
    ),
]
