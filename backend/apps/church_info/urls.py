from django.urls import path

from apps.church_info.views.church_info_views import (
    PublicChurchInformationView,
)

urlpatterns = [
    path(
        "church-info",
        PublicChurchInformationView.as_view(),
        name="public-church-information",
    ),
]
