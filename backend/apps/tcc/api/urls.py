from django.urls import include, path

urlpatterns = [
    path("v1/auth/", include("apps.accounts.urls")),
    path("v1/attendance/", include("apps.attendance.urls")),
    path("v1/finance/", include("apps.finance.urls")),
    path("v1/", include("apps.zones.urls")),
    path(
        "v1/activities/",
        include("apps.activities.urls"),
    ),
]
