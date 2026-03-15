from django.urls import path

from .views import (
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
    path("dashboard/", dashboard, name="dashboard"),
    path("panels/", panel_list, name="panel_list"),
    path("panels/create/", panel_create, name="panel_create"),
    path("panels/<int:panel_id>/", panel_detail, name="panel_detail"),
    path("panels/<int:panel_id>/edit/", panel_update, name="panel_update"),
    path("reservations/", reservation_list, name="reservation_list"),
    path("reservations/create/", reservation_create, name="reservation_create"),
    path("api/panel-faces/", panel_faces_by_agency_api, name="panel_faces_by_agency_api"),
]