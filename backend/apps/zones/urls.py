from django.urls import path

from apps.zones.views.zones_view import (
    ZoneDeactivateView,
    ZoneDetailView,
    ZoneLeaderAssignmentEndView,
    ZoneLeaderAssignmentListCreateView,
    ZoneListCreateView,
)

app_name = "zones"

urlpatterns = [
    path(
        "zones/",
        ZoneListCreateView.as_view(),
        name="zone-list-create",
    ),
    path(
        "zones/<uuid:zone_id>/",
        ZoneDetailView.as_view(),
        name="zone-detail",
    ),
    path(
        "zones/<uuid:zone_id>/deactivate/",
        ZoneDeactivateView.as_view(),
        name="zone-deactivate",
    ),
    path(
        "zones/<uuid:zone_id>/leaders/",
        ZoneLeaderAssignmentListCreateView.as_view(),
        name="zone-leader-list-create",
    ),
    path(
        "zones/<uuid:zone_id>/leaders/<uuid:assignment_id>/end/",
        ZoneLeaderAssignmentEndView.as_view(),
        name="zone-leader-end",
    ),
]
