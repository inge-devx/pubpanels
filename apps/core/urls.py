from django.urls import path

from .public_views import (
    public_catalog,
    public_panel_detail,
    public_reservation_request,
    public_reservation_success,
)
from .views import (
    cities_by_country_api,
    dashboard,
    home,
    panel_create,
    panel_detail,
    panel_faces_by_agency_api,
    panel_list,
    panel_update,
    reservation_create,
    reservation_list,
)

urlpatterns = [
    path("", home, name="home"),
    path("catalog/", public_catalog, name="public_catalog"),
    path("catalog/panels/<int:panel_id>/", public_panel_detail, name="public_panel_detail"),
    path("catalog/panels/<int:panel_id>/request/", public_reservation_request, name="public_reservation_request_for_panel"),
    path("request-reservation/", public_reservation_request, name="public_reservation_request"),
    path("request-reservation/success/", public_reservation_success, name="public_reservation_success"),
    path("dashboard/", dashboard, name="dashboard"),
    path("panels/", panel_list, name="panel_list"),
    path("panels/create/", panel_create, name="panel_create"),
    path("panels/<int:panel_id>/", panel_detail, name="panel_detail"),
    path("panels/<int:panel_id>/edit/", panel_update, name="panel_update"),
    path("reservations/", reservation_list, name="reservation_list"),
    path("reservations/create/", reservation_create, name="reservation_create"),
    path("api/panel-faces/", panel_faces_by_agency_api, name="panel_faces_by_agency_api"),
    path("api/cities/", cities_by_country_api, name="cities_by_country_api"),
]