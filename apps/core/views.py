from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.panels.forms import PanelForm
from apps.panels.models import Panel, PanelFace
from apps.reservations.forms import ReservationForm
from apps.reservations.models import Reservation


def home(request):
    return render(request, "core/home.html")


def get_agency_scoped_panel_or_404(user, panel_id):
    if user.role == user.Role.SUPER_ADMIN:
        return get_object_or_404(
            Panel.objects.select_related("agency").prefetch_related("faces"),
            pk=panel_id,
        )

    if not user.agency:
        raise Http404("No agency is associated with this user.")

    return get_object_or_404(
        Panel.objects.select_related("agency").prefetch_related("faces"),
        pk=panel_id,
        agency=user.agency,
    )


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
def panel_detail(request, panel_id):
    panel = get_agency_scoped_panel_or_404(request.user, panel_id)
    return render(request, "core/panel_detail.html", {"panel": panel})


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
            panel = form.save()
            messages.success(request, "Panneau créé avec succès.")
            return redirect("panel_detail", panel_id=panel.id)
    else:
        form = PanelForm(user=request.user)

    return render(
        request,
        "core/panel_form.html",
        {
            "form": form,
            "page_title": "Créer un panneau",
            "submit_label": "Créer",
        },
    )


@login_required
def panel_update(request, panel_id):
    panel = get_agency_scoped_panel_or_404(request.user, panel_id)

    if request.method == "POST":
        form_data = request.POST.copy()
        if request.user.role != request.user.Role.SUPER_ADMIN:
            form_data["agency"] = str(request.user.agency_id)

        form = PanelForm(form_data, instance=panel, user=request.user)
        if form.is_valid():
            panel = form.save()
            messages.success(request, "Panneau mis à jour avec succès.")
            return redirect("panel_detail", panel_id=panel.id)
    else:
        form = PanelForm(instance=panel, user=request.user)

    return render(
        request,
        "core/panel_form.html",
        {
            "form": form,
            "panel": panel,
            "page_title": "Modifier un panneau",
            "submit_label": "Mettre à jour",
        },
    )


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


@login_required
def panel_faces_by_agency_api(request):
    user = request.user
    agency_id = request.GET.get("agency_id")

    if user.role != user.Role.SUPER_ADMIN:
        if not user.agency_id:
            return JsonResponse({"faces": [], "computed_end_date": None})
        agency_id = str(user.agency_id)

    if not agency_id:
        return JsonResponse({"faces": [], "computed_end_date": None})

    faces = PanelFace.objects.select_related("panel", "panel__agency").filter(
        panel__agency_id=agency_id,
        operational_status=PanelFace.OperationalStatus.AVAILABLE,
    )

    start_date_raw = request.GET.get("start_date")
    duration_months_raw = request.GET.get("duration_months")
    computed_end_date = None

    if start_date_raw and duration_months_raw:
        try:
            start_date = date.fromisoformat(start_date_raw)
            duration_months = int(duration_months_raw)

            if duration_months >= 1:
                computed_end_date = start_date + timedelta(days=(30 * duration_months) - 1)

                faces = faces.exclude(
                    reservations__status__in=[
                        Reservation.Status.APPROVED,
                        Reservation.Status.ACTIVE,
                    ],
                    reservations__start_date__lte=computed_end_date,
                    reservations__end_date__gte=start_date,
                )
        except ValueError:
            computed_end_date = None

    faces = faces.order_by("panel__reference", "code").distinct()

    return JsonResponse(
        {
            "faces": [
                {
                    "id": face.id,
                    "label": str(face),
                    "monthly_price": str(face.monthly_price),
                }
                for face in faces
            ],
            "computed_end_date": computed_end_date.isoformat() if computed_end_date else None,
        }
    )