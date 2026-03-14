from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.panels.models import Panel
from apps.reservations.models import Reservation


def home(request):
    return render(request, "core/home.html")


@login_required
def dashboard(request):
    user = request.user

    if user.role == user.Role.SUPER_ADMIN:
        panels = Panel.objects.all()
        reservations = Reservation.objects.all()
    else:
        panels = Panel.objects.filter(agency=user.agency)
        reservations = Reservation.objects.filter(agency=user.agency)

    context = {
        "panel_count": panels.count(),
        "reservation_count": reservations.count(),
        "pending_count": reservations.filter(status=Reservation.Status.PENDING).count(),
        "active_count": reservations.filter(status=Reservation.Status.ACTIVE).count(),
    }
    return render(request, "core/dashboard.html", context)


@login_required
def panel_list(request):
    user = request.user

    if user.role == user.Role.SUPER_ADMIN:
        panels = Panel.objects.select_related("agency").all()
    else:
        panels = Panel.objects.select_related("agency").filter(agency=user.agency)

    return render(request, "core/panel_list.html", {"panels": panels})


@login_required
def reservation_list(request):
    user = request.user

    if user.role == user.Role.SUPER_ADMIN:
        reservations = Reservation.objects.select_related(
            "agency", "panel_face__panel", "client"
        ).all()
    else:
        reservations = Reservation.objects.select_related(
            "agency", "panel_face__panel", "client"
        ).filter(agency=user.agency)

    return render(
        request,
        "core/reservation_list.html",
        {"reservations": reservations},
    )