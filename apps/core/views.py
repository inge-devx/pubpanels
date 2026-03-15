from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.panels.forms import PanelForm
from apps.panels.models import Panel
from apps.reservations.forms import ReservationForm
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
def panel_create(request):
    if request.user.role != request.user.Role.SUPER_ADMIN and not request.user.agency:
        messages.error(request, "Aucune agence n'est associée à votre compte.")
        return redirect("dashboard")

    if request.method == "POST":
        form_data = request.POST.copy()
        if request.user.role != request.user.Role.SUPER_ADMIN:
            form_data["agency"] = str(request.user.agency_id)

        form = PanelForm(form_data, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Panneau créé avec succès.")
            return redirect("panel_list")
    else:
        form = PanelForm(user=request.user)

    return render(request, "core/panel_form.html", {"form": form})


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


@login_required
def reservation_create(request):
    if request.user.role != request.user.Role.SUPER_ADMIN and not request.user.agency:
        messages.error(request, "Aucune agence n'est associée à votre compte.")
        return redirect("dashboard")

    if request.method == "POST":
        form_data = request.POST.copy()
        if request.user.role != request.user.Role.SUPER_ADMIN:
            form_data["agency"] = str(request.user.agency_id)

        form = ReservationForm(form_data, user=request.user)
        if form.is_valid():
            reservation = form.save(commit=False)

            if request.user.role != request.user.Role.SUPER_ADMIN:
                reservation.agency = request.user.agency

            reservation.created_by = request.user
            reservation.save()

            messages.success(request, "Réservation créée avec succès.")
            return redirect("reservation_list")
    else:
        form = ReservationForm(user=request.user)

    return render(request, "core/reservation_form.html", {"form": form})