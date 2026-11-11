"""URL routes for Attendance session endpoints."""

from django.urls import path

from apps.attendance.views.session_view import (
    AttendanceSessionCloseView,
    AttendanceSessionDetailView,
    AttendanceSessionListCreateView,
    AttendanceSessionOpenView,
)

urlpatterns = [
    path(
        "sessions/",
        AttendanceSessionListCreateView.as_view(),
        name="attendance-session-list-create",
    ),
    path(
        "sessions/<uuid:session_id>/",
        AttendanceSessionDetailView.as_view(),
        name="attendance-session-detail",
    ),
    path(
        "sessions/<uuid:session_id>/open/",
        AttendanceSessionOpenView.as_view(),
        name="attendance-session-open",
    ),
    path(
        "sessions/<uuid:session_id>/close/",
        AttendanceSessionCloseView.as_view(),
        name="attendance-session-close",
    ),
]
