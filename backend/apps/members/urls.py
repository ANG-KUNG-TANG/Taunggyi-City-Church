"""
URL configuration for member management APIs.
"""

from django.urls import path

from apps.members.views.member_views import (
    MemberDetailView,
    MemberListCreateView,
    MemberTransferView,
)

app_name = "members"

urlpatterns = [
    path(
        "",
        MemberListCreateView.as_view(),
        name="member-list-create",
    ),
    path(
        "<uuid:member_id>/",
        MemberDetailView.as_view(),
        name="member-detail",
    ),
    path(
        "<uuid:member_id>/transfer/",
        MemberTransferView.as_view(),
        name="member-transfer",
    ),
]
