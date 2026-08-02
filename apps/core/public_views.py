from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator


from apps.agencies.models import Agency
from apps.core.constants import COUNTRY_CHOICES
from apps.geography.models import GeographicUnit, GeographicLevel
from apps.panels.models import Panel, PanelFace
from apps.reservations.models import Reservation
from apps.reservations.public_forms import PublicReservationRequestForm
from apps.reservations.notifications import send_new_public_reservation_notification

from datetime import datetime, timedelta

def parse_catalog_period(request):
    """
    Retourne (start_date, end_date, selected_start_date, selected_duration_months, period_error)
    """
    selected_start_date = request.GET.get("start_date", "").strip()
    selected_duration_months = request.GET.get("duration_months", "").strip()

    if not selected_start_date and not selected_duration_months:
        return None, None, "", "", ""

    if not selected_start_date or not selected_duration_months:
        return None, None, selected_start_date, selected_duration_months, (
            "Veuillez renseigner à la fois la date de début et le nombre de mois."
        )

    try:
        start_date = datetime.strptime(selected_start_date, "%Y-%m-%d").date()
    except ValueError:
        return None, None, selected_start_date, selected_duration_months, (
            "La date de début fournie est invalide."
        )

    try:
        duration_months = int(selected_duration_months)
    except ValueError:
        return None, None, selected_start_date, selected_duration_months, (
            "Le nombre de mois doit être un entier valide."
        )

    if duration_months < 1:
        return None, None, selected_start_date, selected_duration_months, (
            "Le nombre de mois doit être supérieur ou égal à 1."
        )

    end_date = start_date + timedelta(days=(30 * duration_months) - 1)
    return start_date, end_date, selected_start_date, selected_duration_months, ""

def face_is_publicly_available(face):
    """
    Règle publique actuelle, volontairement stricte :
    - la face doit être opérationnellement AVAILABLE
    - elle ne doit avoir aucune réservation APPROVED ou ACTIVE

    Tant que le vrai filtre par période n'est pas implémenté,
    on choisit une logique conservatrice pour éviter d'afficher
    une face déjà engagée commercialement.
    """
    if face.operational_status != PanelFace.OperationalStatus.AVAILABLE:
        return False

    blocking_statuses = set(Reservation.get_blocking_statuses())

    return not face.reservations.filter(status__in=blocking_statuses).exists()


def public_catalog(request):
    if "confined_agency_slug" in request.session:
        del request.session["confined_agency_slug"]
    selected_country = request.GET.get("country", "").strip()
    selected_city = request.GET.get("city", "").strip()
    selected_agency = request.GET.get("agency", "").strip()
    selected_format_category = request.GET.get("format_category", "").strip()

    requested_start_date, requested_end_date, selected_start_date, selected_duration_months, period_error = parse_catalog_period(request)

    base_qs = Panel.objects.filter(
        is_published=True,
        agency__status=Agency.Status.ACTIVE,
    )

    panels_qs = (
        base_qs.select_related("agency", "geographic_unit")
        .prefetch_related(
            "faces",
            "faces__images",
            "faces__reservations",
        )
        .order_by("country", "geographic_unit__name", "reference")
    )

    if selected_country:
        panels_qs = panels_qs.filter(country=selected_country)

    if selected_city:
        try:
            selected_unit = GeographicUnit.objects.get(pk=selected_city)
            panels_qs = panels_qs.filter(
                geographic_unit_id__in=selected_unit.get_descendant_ids()
            )
        except (GeographicUnit.DoesNotExist, ValueError):
            pass

    if selected_agency:
        panels_qs = panels_qs.filter(agency_id=selected_agency)

    if selected_format_category:
        panels_qs = panels_qs.filter(format_category=selected_format_category)

    panels = []

    for panel in panels_qs:
        available_faces = []

        for face in panel.faces.all():
            if face.is_available_for_period(requested_start_date, requested_end_date):
                available_faces.append(face)

        if not available_faces:
            continue

        available_faces.sort(key=lambda face: face.code)

        panel.public_available_faces = available_faces
        panel.available_faces_count = len(available_faces)
        panel.starting_price = min(face.monthly_price for face in available_faces)

        panels.append(panel)


    paginator = Paginator(panels, 12)
    page_number = request.GET.get("page", "1")
    page_obj = paginator.get_page(page_number)

    querystring = request.GET.copy()
    querystring.pop("page", None)

    # --- Listes de filtres : indépendantes de leur propre critère ---

    available_country_codes = sorted(
        base_qs.order_by().values_list("country", flat=True).distinct()
    )
    countries = [
        {"code": code, "label": dict(COUNTRY_CHOICES).get(code, code)}
        for code in available_country_codes
    ]

    geographic_levels = []
    if selected_country:
        geographic_levels = list(
            GeographicLevel.objects.filter(country__code=selected_country).order_by("order")
        )

    agencies_base_qs = base_qs
    if selected_country:
        agencies_base_qs = agencies_base_qs.filter(country=selected_country)
    if selected_city:
        try:
            selected_unit = GeographicUnit.objects.get(pk=selected_city)
            agencies_base_qs = agencies_base_qs.filter(
                geographic_unit_id__in=selected_unit.get_descendant_ids()
            )
        except (GeographicUnit.DoesNotExist, ValueError):
            pass

    agencies = (
        Agency.objects.filter(
            status=Agency.Status.ACTIVE,
            panels__in=agencies_base_qs,
        )
        .distinct()
        .order_by("name")
    )

    active_filters_count = sum(
        1 for v in [selected_country, selected_city, selected_agency, selected_format_category, selected_start_date]
        if v
    )

    context = {
        "panels": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "querystring": querystring.urlencode(),
        "countries": countries,
        "geographic_levels": geographic_levels,
        "agencies": agencies,
        "format_categories": Panel.FormatCategory.choices,
        "selected_country": selected_country,
        "selected_city": selected_city,
        "selected_agency": selected_agency,
        "selected_format_category": selected_format_category,
        "selected_start_date": selected_start_date,
        "selected_duration_months": selected_duration_months,
        "period_error": period_error,
        "requested_start_date": requested_start_date,
        "requested_end_date": requested_end_date,
        "active_filters_count": active_filters_count,
    }
    return render(request, "public/catalog.html", context)


def public_panel_detail(request, panel_id):
    if "confined_agency_slug" in request.session:
        del request.session["confined_agency_slug"]
    panel = get_object_or_404(
        Panel.objects.select_related("agency", "geographic_unit").prefetch_related(
            "faces",
            "faces__images",
            "faces__reservations",
        ),
        pk=panel_id,
        is_published=True,
        agency__status=Agency.Status.ACTIVE,
    )

    requested_start_date, requested_end_date, selected_start_date, selected_duration_months, period_error = parse_catalog_period(request)

    faces = []
    for face in panel.faces.all():
        if face.is_available_for_period(requested_start_date, requested_end_date):
            faces.append(face)

    faces.sort(key=lambda face: face.code)

    selected_face = None
    selected_face_id = request.GET.get("face", "").strip()

    if selected_face_id:
        for face in faces:
            if str(face.id) == selected_face_id:
                selected_face = face
                break

    if selected_face is None and faces:
        selected_face = faces[0]

    return render(
        request,
        "public/panel_detail.html",
        {
            "panel": panel,
            "faces": faces,
            "selected_face": selected_face,
            "selected_start_date": selected_start_date,
            "selected_duration_months": selected_duration_months,
            "period_error": period_error,
            "requested_start_date": requested_start_date,
            "requested_end_date": requested_end_date,
        },
    )


def public_reservation_request(request, panel_id=None):
    panel = None
    selected_face = None
    face_locked = False

    query_panel_id = request.GET.get("panel", "").strip()
    query_face_id = request.GET.get("face", "").strip()
    requested_start_date, requested_end_date, selected_start_date, selected_duration_months, period_error = parse_catalog_period(
        request)

    if panel_id is not None:
        panel = get_object_or_404(
            Panel.objects.select_related("agency", "geographic_unit").prefetch_related(
                "faces",
                "faces__images",
                "faces__reservations",
            ),
            pk=panel_id,
            is_published=True,
            agency__status=Agency.Status.ACTIVE,
        )
    elif query_panel_id:
        panel = get_object_or_404(
            Panel.objects.select_related("agency", "geographic_unit").prefetch_related(
                "faces",
                "faces__images",
                "faces__reservations",
            ),
            pk=query_panel_id,
            is_published=True,
            agency__status=Agency.Status.ACTIVE,
        )

    if query_face_id:
        face_queryset = PanelFace.objects.select_related(
            "panel",
            "panel__agency",
            "panel__geographic_unit",
        ).prefetch_related("images", "reservations")

        if panel is not None:
            selected_face = get_object_or_404(face_queryset, pk=query_face_id, panel=panel)
        else:
            selected_face = get_object_or_404(face_queryset, pk=query_face_id)
            panel = selected_face.panel

        face_locked = True

    if panel is not None and selected_face is None:
        public_available_faces = [
            face for face in panel.faces.all()
            if face.is_available_for_period()
        ]
        public_available_faces.sort(key=lambda face: face.code)

        if public_available_faces:
            selected_face = public_available_faces[0]

    initial_data = {}
    if selected_face is not None:
        initial_data["panel_face"] = selected_face

    if request.method == "POST":
        post_data = request.POST.copy()

        if face_locked and selected_face is not None:
            post_data["panel_face"] = str(selected_face.id)

        form = PublicReservationRequestForm(
            post_data,
            panel=panel,
            period_start=requested_start_date,
            period_end=requested_end_date,
            initial=initial_data,
        )

        if form.is_valid():
            reservation = form.save()
            send_new_public_reservation_notification(reservation)

            messages.success(
                request,
                f"Votre demande de réservation a été enregistrée sous la référence #{reservation.id}.",
            )
            return redirect("public_reservation_success")
    else:
        form = PublicReservationRequestForm(
            panel=panel,
            period_start=requested_start_date,
            period_end=requested_end_date,
            initial=initial_data,
        )

        # Préremplissage cohérent si on arrive depuis le filtre période
        start_date_from_query = request.GET.get("start_date", "").strip()
        duration_months_from_query = request.GET.get("duration_months", "").strip()

        if start_date_from_query:
            form.fields["start_date"].initial = start_date_from_query
        if duration_months_from_query:
            form.fields["duration_months"].initial = duration_months_from_query

    return render(
        request,
        "public/reservation_request.html",
        {
            "form": form,
            "panel": panel,
            "selected_face": selected_face,
            "face_locked": face_locked,
            "selected_start_date": selected_start_date,
            "selected_duration_months": selected_duration_months,
            "requested_start_date": requested_start_date,
            "requested_end_date": requested_end_date,
            "period_error": period_error,
        },
    )


def public_reservation_success(request):
    return render(request, "public/reservation_success.html")

def private_agency_catalog(request, agency_slug):
    catalog_agency = get_object_or_404(
        Agency,
        slug=agency_slug,
        status=Agency.Status.ACTIVE,
    )
    request.session["confined_agency_slug"] = catalog_agency.slug

    selected_country = request.GET.get("country", "").strip()
    selected_city = request.GET.get("city", "").strip()
    selected_format_category = request.GET.get("format_category", "").strip()

    (
        requested_start_date,
        requested_end_date,
        selected_start_date,
        selected_duration_months,
        period_error,
    ) = parse_catalog_period(request)

    base_qs = Panel.objects.filter(
        agency=catalog_agency,
        is_published=True,
        agency__status=Agency.Status.ACTIVE,
    )

    panels_qs = (
        base_qs.select_related("agency", "geographic_unit")
        .prefetch_related(
            "faces",
            "faces__images",
            "faces__reservations",
        )
        .order_by("country", "geographic_unit__name", "reference")
    )

    if selected_country:
        panels_qs = panels_qs.filter(country=selected_country)

    if selected_city:
        try:
            selected_unit = GeographicUnit.objects.get(pk=selected_city)
            panels_qs = panels_qs.filter(
                geographic_unit_id__in=selected_unit.get_descendant_ids()
            )
        except (GeographicUnit.DoesNotExist, ValueError):
            pass

    if selected_format_category:
        panels_qs = panels_qs.filter(format_category=selected_format_category)

    panels = []

    for panel in panels_qs:
        available_faces = []

        for face in panel.faces.all():
            if face.is_available_for_period(requested_start_date, requested_end_date):
                available_faces.append(face)

        if not available_faces:
            continue

        available_faces.sort(key=lambda face: face.code)

        panel.public_available_faces = available_faces
        panel.available_faces_count = len(available_faces)
        panel.starting_price = min(face.monthly_price for face in available_faces)

        panels.append(panel)

    paginator = Paginator(panels, 12)
    page_number = request.GET.get("page", "1")
    page_obj = paginator.get_page(page_number)

    querystring = request.GET.copy()
    querystring.pop("page", None)

    # --- Listes de filtres : indépendantes de leur propre critère ---

    available_country_codes = sorted(
        base_qs.order_by().values_list("country", flat=True).distinct()
    )
    countries = [
        {"code": code, "label": dict(COUNTRY_CHOICES).get(code, code)}
        for code in available_country_codes
    ]

    geographic_levels = []
    if selected_country:
        geographic_levels = list(
            GeographicLevel.objects.filter(country__code=selected_country).order_by("order")
        )

    active_filters_count = sum(
        1 for v in [selected_country, selected_city, selected_format_category, selected_start_date]
        if v
    )

    context = {
        "panels": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "querystring": querystring.urlencode(),
        "countries": countries,
        "geographic_levels": geographic_levels,
        "agencies": Agency.objects.none(),
        "format_categories": Panel.FormatCategory.choices,
        "selected_country": selected_country,
        "selected_city": selected_city,
        "selected_agency": "",
        "selected_format_category": selected_format_category,
        "selected_start_date": selected_start_date,
        "selected_duration_months": selected_duration_months,
        "period_error": period_error,
        "requested_start_date": requested_start_date,
        "requested_end_date": requested_end_date,
        "is_private_catalog": True,
        "catalog_agency": catalog_agency,
        "active_filters_count": active_filters_count,
    }

    return render(request, "public/catalog.html", context)


def private_agency_panel_detail(request, agency_slug, panel_id):
    catalog_agency = get_object_or_404(
        Agency,
        slug=agency_slug,
        status=Agency.Status.ACTIVE,
    )
    request.session["confined_agency_slug"] = catalog_agency.slug

    panel = get_object_or_404(
        Panel.objects.select_related("agency", "geographic_unit").prefetch_related(
            "faces",
            "faces__images",
            "faces__reservations",
        ),
        pk=panel_id,
        agency=catalog_agency,
        is_published=True,
        agency__status=Agency.Status.ACTIVE,
    )

    (
        requested_start_date,
        requested_end_date,
        selected_start_date,
        selected_duration_months,
        period_error,
    ) = parse_catalog_period(request)

    faces = []

    for face in panel.faces.all():
        if face.is_available_for_period(requested_start_date, requested_end_date):
            faces.append(face)

    faces.sort(key=lambda face: face.code)

    selected_face = None
    selected_face_id = request.GET.get("face", "").strip()

    if selected_face_id:
        for face in faces:
            if str(face.id) == selected_face_id:
                selected_face = face
                break

    if selected_face is None and faces:
        selected_face = faces[0]

    return render(
        request,
        "public/panel_detail.html",
        {
            "panel": panel,
            "faces": faces,
            "selected_face": selected_face,
            "selected_start_date": selected_start_date,
            "selected_duration_months": selected_duration_months,
            "period_error": period_error,
            "requested_start_date": requested_start_date,
            "requested_end_date": requested_end_date,
            "is_private_catalog": True,
            "catalog_agency": catalog_agency,
        },
    )