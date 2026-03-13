from django.urls import include, path

urlpatterns = [
    path("auth/", include("bodepontoio.urls")),
    path("geo/", include("bodepontoio.geo.urls")),
]
