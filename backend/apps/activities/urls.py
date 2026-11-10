"""
URL routes for Activity endpoints.
"""

from django.urls import path

from apps.activities.views.activities_view import (
    ActivityArchiveView,
    ActivityCreateView,
    ActivityManagementDetailView,
    ActivityManagementListView,
    ActivityPublishView,
    PublicActivityDetailView,
    PublicActivityListView,
)

urlpatterns = [
    path("", PublicActivityListView.as_view(), name="activity-public-list"),
    path(
        "public/<uuid:activity_id>/",
        PublicActivityDetailView.as_view(),
        name="activity-public-detail",
    ),
    path(
        "manage/",
        ActivityManagementListView.as_view(),
        name="activity-management-list",
    ),
    path(
        "manage/create/",
        ActivityCreateView.as_view(),
        name="activity-create",
    ),
    path(
        "manage/<uuid:activity_id>/",
        ActivityManagementDetailView.as_view(),
        name="activity-management-detail",
    ),
    path(
        "manage/<uuid:activity_id>/publish/",
        ActivityPublishView.as_view(),
        name="activity-publish",
    ),
    path(
        "manage/<uuid:activity_id>/archive/",
        ActivityArchiveView.as_view(),
        name="activity-archive",
    ),
]
