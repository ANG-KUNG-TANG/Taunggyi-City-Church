"""
URL routes for shared content media operations.
"""

from django.urls import path

from apps.content_media.views.media_views import (
    MediaDeleteView,
    MediaFileView,
)

urlpatterns = [
    path(
        "<uuid:media_id>/file/",
        MediaFileView.as_view(),
        name="content-media-file",
    ),
    path(
        "manage/<uuid:media_id>/",
        MediaDeleteView.as_view(),
        name="content-media-delete",
    ),
]
