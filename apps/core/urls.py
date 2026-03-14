from django.urls import path

from .views import dashboard, home, panel_create, panel_list, reservation_list

urlpatterns = [
    path("", home, name="home"),
    path("dashboard/", dashboard, name="dashboard"),
    path("panels/", panel_list, name="panel_list"),
    path("panels/create/", panel_create, name="panel_create"),
    path("reservations/", reservation_list, name="reservation_list"),
]
