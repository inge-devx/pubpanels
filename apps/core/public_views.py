from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.agencies.models import Agency
from apps.core.constants import COUNTRY_CHOICES
from apps.locations.models import City
from apps.panels.models import Panel
from apps.reservations.public_forms import PublicReservationRequestForm


def public_catalog(request):
    base_panels = Panel.objects.select_related("agency", "city_ref").prefetch_related("faces").filter(
        is_published=True,
        agency__status=Agency.Status.ACTIVE,
    )

    panels = base_panels.order_by("country", "city", "reference")

    selected_country = request.GET.get("country", "").strip()
    selected_city = request.GET.get("city", "").strip()
    selected_agency = request.GET.get("agency", "").strip()
    selected_format_category = request.GET.get("format_category", "").strip()

    if selected_country:
        panels = panels.filter(country=selected_country)

    if selected_city:
        panels = panels.filter(city_ref_id=selected_city)

    if selected_agency:
        panels = panels.filter(agency_id=selected_agency)

    if selected_format_category:
        panels = panels.filter(format_category=selected_format_category)

    available_country_codes = list(
        base_panels.values_list("country", flat=True).distinct().order_by("country")
    )
    countries = [
        {"code": code, "label": dict(COUNTRY_CHOICES).get(code, code)}
        for code in available_country_codes
    ]

    cities = City.objects.none()
    if selected_country:
        cities = City.objects.filter(
            country_code=selected_country,
            is_active=True,
            panels__is_published=True,
            panels__agency__status=Agency.Status.ACTIVE,
            panels__country=selected_country,
        ).distinct().order_by("name")

    agencies = Agency.objects.filter(
        status=Agency.Status.ACTIVE,
        panels__is_published=True,
    ).distinct().order_by("name")

    if selected_country:
        agencies = agencies.filter(panels__country=selected_country).distinct()

    if selected_city:
        agencies = agencies.filter(panels__city_ref_id=selected_city).distinct()

    context = {
        "panels": panels,
        "countries": countries,
        "cities": cities,
        "agencies": agencies,
        "format_categories": Panel.FormatCategory.choices,
        "selected_country": selected_country,
        "selected_city": selected_city,
        "selected_agency": selected_agency,
        "selected_format_category": selected_format_category,
    }
    return render(request, "public/catalog.html", context)


def public_panel_detail(request, panel_id):
    panel = get_object_or_404(
        Panel.objects.select_related("agency", "city_ref").prefetch_related("faces"),
        pk=panel_id,
        is_published=True,
        agency__status=Agency.Status.ACTIVE,
    )

    return render(request, "public/panel_detail.html", {"panel": panel})


def public_reservation_request(request, panel_id=None):
    panel = None
    if panel_id is not None:
        panel = get_object_or_404(
            Panel.objects.select_related("agency", "city_ref").prefetch_related("faces"),
            pk=panel_id,
            is_published=True,
            agency__status=Agency.Status.ACTIVE,
        )

    if request.method == "POST":
        form = PublicReservationRequestForm(request.POST, panel=panel)
        if form.is_valid():
            reservation = form.save()
            messages.success(
                request,
                f"Votre demande de réservation a été enregistrée sous la référence #{reservation.id}.",
            )
            return redirect("public_reservation_success")
    else:
        form = PublicReservationRequestForm(panel=panel)

    return render(
        request,
        "public/reservation_request.html",
        {
            "form": form,
            "panel": panel,
        },
    )


def public_reservation_success(request):
    return render(request, "public/reservation_success.html")