"""
URL configuration for the Announcement API.
"""

from django.urls import path

from apps.announcements.views.announcement_views import (
    AnnouncementArchiveView,
    AnnouncementCreateView,
    AnnouncementManagementDetailView,
    AnnouncementManagementListView,
    AnnouncementPublishView,
    PublicAnnouncementDetailView,
    PublicAnnouncementListView,
)

urlpatterns = [
    path("", PublicAnnouncementListView.as_view(), name="public-announcement-list"),
    path(
        "public/<uuid:announcement_id>/",
        PublicAnnouncementDetailView.as_view(),
        name="public-announcement-detail",
    ),
    path(
        "manage/",
        AnnouncementManagementListView.as_view(),
        name="announcement-management-list",
    ),
    path(
        "manage/create/",
        AnnouncementCreateView.as_view(),
        name="announcement-create",
    ),
    path(
        "manage/<uuid:announcement_id>/",
        AnnouncementManagementDetailView.as_view(),
        name="announcement-management-detail",
    ),
    path(
        "manage/<uuid:announcement_id>/publish/",
        AnnouncementPublishView.as_view(),
        name="announcement-publish",
    ),
    path(
        "manage/<uuid:announcement_id>/archive/",
        AnnouncementArchiveView.as_view(),
        name="announcement-archive",
    ),
]
