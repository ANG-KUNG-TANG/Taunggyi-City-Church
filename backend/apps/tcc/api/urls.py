from django.urls import include, path

urlpatterns = [
    path("v1/attendance/", include("apps.attendance.urls")),
    path("v1/", include("apps.zones.urls")),
    path(
        "v1/activities/",
        include("apps.activities.urls"),
    ),
]
