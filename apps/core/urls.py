from django.urls import path
from .views import home, dashboard, panel_list, reservation_list

urlpatterns = [
    path("", home, name="home"),
    path("dashboard/", dashboard, name="dashboard"),
    path("panels/", panel_list, name="panel_list"),
    path("reservations/", reservation_list, name="reservation_list"),
]