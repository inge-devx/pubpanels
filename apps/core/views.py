from datetime import date, timedelta
from django.utils import timezone as django_timezone

from django.utils import timezone
from reportlab.lib.utils import ImageReader



from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.geography.models import GeographicUnit, GeographicLevel
from apps.panels.forms import PanelForm, PanelFaceForm, PanelFaceImageForm
from apps.panels.models import Panel, PanelFace, PanelFaceImage, PanelImportBatch, PanelImportRow
from apps.panels.import_utils import parse_excel_grid, get_agency_initials, suggest_next_reference


from apps.reservations.forms import ReservationForm, ReservationUpdateForm
from apps.reservations.models import Reservation, ReservationStatusLog
from apps.reservations.notifications import send_client_reservation_status_notification
from apps.reservations.models import ReservationTaxLine
from apps.reservations.forms_tax_lines import ReservationTaxLineForm

from django.db.models import Count, Max, Q
from apps.reservations.models import Client
from apps.reservations.forms_clients import ClientForm

from django.http import HttpResponse, Http404
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from apps.agencies.models import Agency
from apps.agencies.forms import AgencyForm, AgencyProfileForm

from django.urls import reverse
import qrcode
import io


def home(request):
    return render(request, "public/home.html")


def get_agency_scoped_panel_or_404(user, panel_id):
    if user.role == user.Role.SUPER_ADMIN:
        return get_object_or_404(
            Panel.objects.select_related("agency", "geographic_unit").prefetch_related("faces"),
            pk=panel_id,
        )

    if not user.agency:
        raise Http404("No agency is associated with this user.")

    return get_object_or_404(
        Panel.objects.select_related("agency", "geographic_unit").prefetch_related("faces"),
        pk=panel_id,
        agency=user.agency,
    )


def get_agency_scoped_reservation_or_404(user, reservation_id):
    queryset = Reservation.objects.select_related(
        "agency",
        "panel_face__panel",
        "client",
        "created_by",
    ).prefetch_related("status_logs__changed_by")

    if user.role == user.Role.SUPER_ADMIN:
        return get_object_or_404(queryset, pk=reservation_id)

    if not user.agency:
        raise Http404("No agency is associated with this user.")

    return get_object_or_404(queryset, pk=reservation_id, agency=user.agency)

from decimal import Decimal

def format_money(value):
    return f"{Decimal(value):.2f}"


@login_required
def dashboard(request):
    user = request.user

    if user.role == user.Role.SUPER_ADMIN:
        panels = Panel.objects.all()
        reservations_base = Reservation.objects.select_related(
            "agency",
            "panel_face__panel",
            "client",
        ).all()
        panel_faces = PanelFace.objects.select_related("panel", "panel__agency").all()
    else:
        panels = Panel.objects.filter(agency=user.agency)
        reservations_base = Reservation.objects.select_related(
            "agency",
            "panel_face__panel",
            "client",
        ).filter(agency=user.agency)
        panel_faces = PanelFace.objects.select_related("panel", "panel__agency").filter(
            panel__agency=user.agency
        )

    today = date.today()
    upcoming_limit = today + timedelta(days=7)

    start_date_str = request.GET.get("start_date", "").strip()
    end_date_str = request.GET.get("end_date", "").strip()

    filter_start_date = None
    filter_end_date = None
    date_filter_error = None

    if start_date_str:
        try:
            filter_start_date = date.fromisoformat(start_date_str)
        except ValueError:
            date_filter_error = "La date de début est invalide."

    if end_date_str:
        try:
            filter_end_date = date.fromisoformat(end_date_str)
        except ValueError:
            date_filter_error = "La date de fin est invalide."

    if (
        date_filter_error is None
        and filter_start_date
        and filter_end_date
        and filter_start_date > filter_end_date
    ):
        date_filter_error = "La date de début doit être inférieure ou égale à la date de fin."

    reservations = reservations_base
    if date_filter_error is None:
        if filter_start_date:
            reservations = reservations.filter(created_at__date__gte=filter_start_date)
        if filter_end_date:
            reservations = reservations.filter(created_at__date__lte=filter_end_date)

    active_reservations = reservations.filter(status=Reservation.Status.ACTIVE)
    pending_reservations = reservations.filter(status=Reservation.Status.PENDING)
    approved_reservations = reservations.filter(status=Reservation.Status.APPROVED)
    completed_reservations = reservations.filter(status=Reservation.Status.COMPLETED)

    occupied_face_ids = active_reservations.values_list("panel_face_id", flat=True).distinct()
    occupied_faces_count = panel_faces.filter(id__in=occupied_face_ids).count()
    total_faces_count = panel_faces.count()
    available_faces_count = max(total_faces_count - occupied_faces_count, 0)

    occupancy_rate = 0
    if total_faces_count > 0:
        occupancy_rate = round((occupied_faces_count / total_faces_count) * 100, 2)

    recent_reservations = reservations.order_by("-created_at")[:5]

    ending_soon_reservations = active_reservations.filter(
        end_date__gte=today,
        end_date__lte=upcoming_limit,
    ).order_by("end_date")[:10]

    from decimal import Decimal

    def sum_total_price(queryset):
        total = queryset.aggregate(total=Sum("total_price"))["total"]
        total = total or Decimal("0.00")
        return total.quantize(Decimal("0.00"))

    total_revenue = sum_total_price(reservations)
    committed_revenue = sum_total_price(
        reservations.filter(
            status__in=[Reservation.Status.APPROVED, Reservation.Status.ACTIVE]
        )
    )
    active_revenue = sum_total_price(active_reservations)
    completed_revenue = sum_total_price(completed_reservations)

    context = {
        "panel_count": panels.count(),
        "reservation_count": reservations.count(),
        "pending_count": pending_reservations.count(),
        "approved_count": approved_reservations.count(),
        "active_count": active_reservations.count(),
        "completed_count": completed_reservations.count(),
        "total_faces_count": total_faces_count,
        "occupied_faces_count": occupied_faces_count,
        "available_faces_count": available_faces_count,
        "occupancy_rate": occupancy_rate,
        "recent_reservations": recent_reservations,
        "ending_soon_reservations": ending_soon_reservations,
        "today": today,
        "upcoming_limit": upcoming_limit,

        "total_revenue": total_revenue,
        "committed_revenue": committed_revenue,
        "active_revenue": active_revenue,
        "completed_revenue": completed_revenue,

        "start_date": start_date_str,
        "end_date": end_date_str,
        "date_filter_error": date_filter_error,
    }
    return render(request, "core/dashboard.html", context)


@login_required
def action_center(request):
    user = request.user
    today = date.today()

    base_qs = Reservation.objects.select_related("agency", "panel_face__panel", "client")
    if user.role != user.Role.SUPER_ADMIN:
        base_qs = base_qs.filter(agency=user.agency)

    to_process = base_qs.filter(status=Reservation.Status.PENDING).order_by("created_at")

    to_activate = base_qs.filter(
        status=Reservation.Status.APPROVED,
        start_date__lte=today,
    ).order_by("start_date")

    to_close = base_qs.filter(
        status=Reservation.Status.ACTIVE,
        end_date__lt=today,
    ).order_by("end_date")

    context = {
        "to_process": to_process,
        "to_activate": to_activate,
        "to_close": to_close,
        "today": today,
    }
    return render(request, "core/action_center.html", context)


@login_required
def panel_list(request):
    user = request.user

    if user.role == user.Role.SUPER_ADMIN:
        panels = Panel.objects.select_related("agency", "geographic_unit").all()
    else:
        panels = Panel.objects.select_related("agency", "geographic_unit").filter(agency=user.agency)

    return render(request, "core/panel_list.html", {"panels": panels})



@login_required
def panel_detail(request, panel_id):
    panel = get_agency_scoped_panel_or_404(request.user, panel_id)
    return render(request, "core/panel_detail.html", {"panel": panel})

@login_required
def panel_qr_code_image(request, panel_id):
    panel = get_agency_scoped_panel_or_404(request.user, panel_id)

    target_url = request.build_absolute_uri(
        reverse("private_agency_panel_detail", args=[panel.agency.slug, panel.id])
    )

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=20,
        border=4,
    )
    qr.add_data(target_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return HttpResponse(buffer.getvalue(), content_type="image/png")


@login_required
def panel_qr_print(request, panel_id):
    panel = get_agency_scoped_panel_or_404(request.user, panel_id)
    return render(request, "core/panel_qr_print.html", {"panel": panel})


@login_required
def panel_create(request):
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
            "panel": None,
            "page_title": "Créer un panneau",
            "submit_label": "Créer le panneau",
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
def panel_face_create(request, panel_id):
    panel = get_agency_scoped_panel_or_404(request.user, panel_id)

    if request.method == "POST":
        form_data = request.POST.copy()
        form_data["panel"] = str(panel.id)

        form = PanelFaceForm(form_data)
        if form.is_valid():
            face = form.save()
            messages.success(request, "Face créée avec succès.")
            return redirect("panel_face_detail", face_id=face.id)
    else:
        form = PanelFaceForm(initial={"panel": panel})

    return render(
        request,
        "core/panel_face_form.html",
        {
            "form": form,
            "panel": panel,
            "face": None,
            "page_title": f"Créer une face pour {panel.reference}",
            "submit_label": "Créer la face",
        },
    )


@login_required
def panel_face_update(request, face_id):
    face = get_object_or_404(
        PanelFace.objects.select_related("panel", "panel__agency"),
        pk=face_id,
    )

    get_agency_scoped_panel_or_404(request.user, face.panel_id)

    if request.method == "POST":
        form_data = request.POST.copy()
        form_data["panel"] = str(face.panel_id)

        form = PanelFaceForm(form_data, instance=face)
        if form.is_valid():
            face = form.save()
            messages.success(request, "Face mise à jour avec succès.")
            return redirect("panel_face_detail", face_id=face.id)
    else:
        form = PanelFaceForm(instance=face)

    return render(
        request,
        "core/panel_face_form.html",
        {
            "form": form,
            "panel": face.panel,
            "face": face,
            "page_title": f"Modifier la face {face.code} de {face.panel.reference}",
            "submit_label": "Mettre à jour la face",
        },
    )

@login_required
def panel_face_detail(request, face_id):
    face = get_object_or_404(
        PanelFace.objects
        .select_related("panel", "panel__agency")
        .prefetch_related("images"),
        pk=face_id,
    )

    get_agency_scoped_panel_or_404(request.user, face.panel_id)

    return render(
        request,
        "core/panel_face_detail.html",
        {
            "face": face,
            "panel": face.panel,
        },
    )

@login_required
def panel_face_image_create(request, face_id):
    face = get_object_or_404(
        PanelFace.objects.select_related("panel", "panel__agency"),
        pk=face_id,
    )

    get_agency_scoped_panel_or_404(request.user, face.panel_id)

    if request.method == "POST":
        form = PanelFaceImageForm(request.POST, request.FILES)
        form.data = form.data.copy()
        form.data["face"] = str(face.id)

        if form.is_valid():
            image = form.save()
            messages.success(request, "Image de face ajoutée avec succès.")
            return redirect("panel_face_detail", face_id=image.face_id)
    else:
        form = PanelFaceImageForm(initial={"face": face})

    return render(
        request,
        "core/panel_face_image_form.html",
        {
            "form": form,
            "face": face,
            "panel": face.panel,
            "image_obj": None,
            "page_title": f"Ajouter une image à la face {face.code}",
            "submit_label": "Ajouter l’image",
        },
    )


@login_required
def panel_face_image_update(request, image_id):
    image_obj = get_object_or_404(
        PanelFaceImage.objects.select_related("face", "face__panel", "face__panel__agency"),
        pk=image_id,
    )

    get_agency_scoped_panel_or_404(request.user, image_obj.face.panel_id)

    if request.method == "POST":
        form = PanelFaceImageForm(request.POST, request.FILES, instance=image_obj)
        form.data = form.data.copy()
        form.data["face"] = str(image_obj.face_id)

        if form.is_valid():
            image_obj = form.save()
            messages.success(request, "Image de face mise à jour avec succès.")
            return redirect("panel_face_detail", face_id=image_obj.face_id)
    else:
        form = PanelFaceImageForm(instance=image_obj)

    return render(
        request,
        "core/panel_face_image_form.html",
        {
            "form": form,
            "face": image_obj.face,
            "panel": image_obj.face.panel,
            "image_obj": image_obj,
            "page_title": f"Modifier l’image de la face {image_obj.face.code}",
            "submit_label": "Mettre à jour l’image",
        },
    )

@login_required
def panel_import_upload(request):
    if not request.user.agency and request.user.role != request.user.Role.SUPER_ADMIN:
        messages.error(request, "Aucune régie n'est associée à votre compte.")
        return redirect("dashboard")

    if request.method == "POST":
        uploaded_file = request.FILES.get("file")
        if not uploaded_file or not uploaded_file.name.lower().endswith(".xlsx"):
            messages.error(request, "Veuillez sélectionner un fichier .xlsx valide.")
            return redirect("panel_import_upload")

        try:
            grid = parse_excel_grid(uploaded_file)
        except Exception:
            messages.error(request, "Impossible de lire ce fichier. Vérifiez qu’il s’agit bien d’un fichier Excel valide.")
            return redirect("panel_import_upload")

        if not grid:
            messages.error(request, "Ce fichier semble vide.")
            return redirect("panel_import_upload")

        agency = request.user.agency
        batch = PanelImportBatch.objects.create(
            agency=agency,
            created_by=request.user,
            source_filename=uploaded_file.name,
            reference_prefix=get_agency_initials(agency),
            raw_grid=grid,
            status=PanelImportBatch.Status.CONFIGURING,
        )

        return redirect("panel_import_configure", batch_id=batch.id)
    else:
        return render(request, "core/panel_import_upload.html")


@login_required
def panel_import_configure(request, batch_id):
    batch = _get_scoped_batch_or_404(request.user, batch_id)

    if batch.status != PanelImportBatch.Status.CONFIGURING or not batch.raw_grid:
        return redirect("panel_import_wizard", batch_id=batch.id)

    if request.method == "POST":
        raw_indices = request.POST.getlist("header_rows")
        try:
            header_indices = sorted({int(i) for i in raw_indices})
        except ValueError:
            header_indices = []

        grid = batch.raw_grid

        if not header_indices or any(not (0 <= i < len(grid)) for i in header_indices):
            messages.error(request, "Sélectionnez au moins une ligne d’en-têtes valide.")
            return redirect("panel_import_configure", batch_id=batch.id)

        max_header_index = max(header_indices)
        column_count = max(len(grid[i]) for i in header_indices)

        headers = []
        for col in range(column_count):
            parts = []
            for row_i in header_indices:
                row = grid[row_i]
                if col < len(row) and row[col]["v"]:
                    parts.append(row[col]["v"])
            headers.append(" - ".join(parts))

        data_rows = grid[max_header_index + 1:]

        row_count = 0
        for row_cells in data_rows:
            if not any(cell["v"] for cell in row_cells):
                continue
            row_count += 1
            PanelImportRow.objects.create(
                batch=batch,
                row_index=row_count,
                headers=headers,
                values=row_cells,
            )

        if row_count == 0:
            messages.error(request, "Aucune ligne de donnée trouvée après ces en-têtes.")
            return redirect("panel_import_configure", batch_id=batch.id)

        batch.raw_grid = None
        batch.status = PanelImportBatch.Status.IN_PROGRESS
        batch.save(update_fields=["raw_grid", "status"])

        messages.success(request, f"{row_count} ligne(s) prête(s). Traitons-les une par une.")
        return redirect("panel_import_wizard", batch_id=batch.id)

    preview_rows = batch.raw_grid[:30]
    return render(
        request,
        "core/panel_import_configure.html",
        {"batch": batch, "preview_rows": preview_rows, "truncated": len(batch.raw_grid) > 30},
    )


@login_required
def panel_import_cancel(request, batch_id):
    if request.method != "POST":
        raise Http404("Invalid method.")

    batch = _get_scoped_batch_or_404(request.user, batch_id)
    batch.delete()
    messages.success(request, "Import annulé.")
    return redirect("panel_import_batch_list")


@login_required
def panel_import_batch_list(request):
    if request.user.role == request.user.Role.SUPER_ADMIN:
        batches = PanelImportBatch.objects.select_related("agency").all()
    else:
        batches = PanelImportBatch.objects.filter(agency=request.user.agency)

    return render(request, "core/panel_import_batch_list.html", {"batches": batches})


def _get_scoped_batch_or_404(user, batch_id):
    if user.role == user.Role.SUPER_ADMIN:
        return get_object_or_404(PanelImportBatch, pk=batch_id)
    return get_object_or_404(PanelImportBatch, pk=batch_id, agency=user.agency)

def _looks_like_separator_row(values, headers_count):
    non_empty = sum(1 for cell in values if cell.get("v"))
    return non_empty <= 1 or non_empty < max(2, headers_count // 4)

@login_required
def panel_import_wizard(request, batch_id):
    batch = _get_scoped_batch_or_404(request.user, batch_id)

    current_row = batch.rows.filter(status=PanelImportRow.Status.PENDING).order_by("row_index").first()

    if current_row is None:
        if batch.status != PanelImportBatch.Status.COMPLETED:
            batch.status = PanelImportBatch.Status.COMPLETED
            batch.completed_at = django_timezone.now()
            batch.save(update_fields=["status", "completed_at"])
        return redirect("panel_import_summary", batch_id=batch.id)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "skip":
            current_row.status = PanelImportRow.Status.SKIPPED
            current_row.save(update_fields=["status"])
            messages.info(request, f"Ligne {current_row.row_index} ignorée.")
            return redirect("panel_import_wizard", batch_id=batch.id)

        reference = request.POST.get("reference", "").strip()
        geographic_unit_id = request.POST.get("geographic_unit", "").strip()
        address = request.POST.get("address", "").strip()
        title = request.POST.get("title", "").strip()

        errors = []

        if not reference:
            errors.append("La référence est obligatoire.")
        elif Panel.objects.filter(agency=batch.agency, reference=reference).exists():
            errors.append(f"La référence « {reference} » existe déjà pour cette régie.")

        geographic_unit = None
        if not geographic_unit_id:
            errors.append("La localisation est obligatoire.")
        else:
            try:
                geographic_unit = GeographicUnit.objects.get(pk=geographic_unit_id)
            except (GeographicUnit.DoesNotExist, ValueError):
                errors.append("Localisation invalide.")

        face_codes = request.POST.getlist("face_codes")
        if len(face_codes) != len(set(face_codes)):
            errors.append("Deux faces ne peuvent pas avoir le même code.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect("panel_import_wizard", batch_id=batch.id)

        panel = Panel(
            agency=batch.agency,
            reference=reference,
            title=title,
            country=batch.agency.country,
            geographic_unit=geographic_unit,
            address=address,
            status=Panel.Status.ACTIVE,
            is_published=True,
        )
        panel.save()

        for code in face_codes:
            is_available = request.POST.get(f"face_{code}_available") == "on"
            PanelFace.objects.create(
                panel=panel,
                code=code,
                monthly_price=0,
                operational_status=(
                    PanelFace.OperationalStatus.AVAILABLE
                    if is_available
                    else PanelFace.OperationalStatus.UNAVAILABLE
                ),
            )

        current_row.status = PanelImportRow.Status.CREATED
        current_row.created_panel = panel
        current_row.save(update_fields=["status", "created_panel"])

        batch.last_geographic_unit = geographic_unit
        batch.next_reference_number += 1
        batch.save(update_fields=["last_geographic_unit", "next_reference_number"])

        messages.success(request, f"Panneau {reference} créé.")
        return redirect("panel_import_wizard", batch_id=batch.id)

    suggested_reference, _ = suggest_next_reference(batch)

    created_count = batch.rows.filter(status=PanelImportRow.Status.CREATED).count()
    skipped_count = batch.rows.filter(status=PanelImportRow.Status.SKIPPED).count()
    remaining_count = batch.total_rows - created_count - skipped_count
    is_likely_separator = _looks_like_separator_row(current_row.values, len(current_row.headers))

    context = {
        "batch": batch,
        "row": current_row,
        "suggested_reference": suggested_reference,
        "last_geographic_unit": batch.last_geographic_unit,
        "created_count": created_count,
        "skipped_count": skipped_count,
        "remaining_count": remaining_count,
        "is_likely_separator": is_likely_separator,
    }
    return render(request, "core/panel_import_wizard.html", context)


@login_required
def panel_import_summary(request, batch_id):
    batch = _get_scoped_batch_or_404(request.user, batch_id)

    created_count = batch.rows.filter(status=PanelImportRow.Status.CREATED).count()
    skipped_count = batch.rows.filter(status=PanelImportRow.Status.SKIPPED).count()

    return render(
        request,
        "core/panel_import_summary.html",
        {"batch": batch, "created_count": created_count, "skipped_count": skipped_count},
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

    status_filter = request.GET.get("status", "").strip()
    if status_filter:
        reservations = reservations.filter(status=status_filter)

    context = {
        "reservations": reservations.order_by("-created_at"),
        "selected_status": status_filter,
        "status_choices": Reservation.Status.choices,
    }

    return render(request, "core/reservation_list.html", context)


@login_required
def reservation_detail(request, reservation_id):
    reservation = get_agency_scoped_reservation_or_404(request.user, reservation_id)
    return render(request, "core/reservation_detail.html", {"reservation": reservation})


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
            return redirect("reservation_detail", reservation_id=reservation.id)
    else:
        initial_data = {}

        client_id = request.GET.get("client_id")
        if client_id:
            initial_data["client"] = client_id

        form = ReservationForm(user=request.user, initial=initial_data)

    return render(
        request,
        "core/reservation_form.html",
        {
            "form": form,
            "page_title": "Créer une réservation",
            "submit_label": "Créer",
        },
    )


@login_required
def reservation_update(request, reservation_id):
    reservation = get_agency_scoped_reservation_or_404(request.user, reservation_id)

    editable_statuses = {
        Reservation.Status.PENDING,
    }

    if reservation.status not in editable_statuses:
        messages.error(
            request,
            "Cette réservation ne peut plus être modifiée dans son statut actuel.",
        )
        return redirect("reservation_detail", reservation_id=reservation.id)

    if request.method == "POST":
        form = ReservationUpdateForm(
            request.POST,
            instance=reservation,
            user=request.user,
            reservation=reservation,
        )
        if form.is_valid():
            reservation = form.save()
            messages.success(request, "Réservation mise à jour avec succès.")
            return redirect("reservation_detail", reservation_id=reservation.id)
    else:
        form = ReservationUpdateForm(
            instance=reservation,
            user=request.user,
            reservation=reservation,
        )

    return render(
        request,
        "core/reservation_form.html",
        {
            "form": form,
            "reservation": reservation,
            "page_title": "Modifier une réservation",
            "submit_label": "Mettre à jour",
        },
    )


@login_required
def reservation_change_status(request, reservation_id, new_status):
    if request.method != "POST":
        raise Http404("Invalid method.")

    reservation = get_agency_scoped_reservation_or_404(request.user, reservation_id)

    allowed_transitions = {
        Reservation.Status.PENDING: {
            Reservation.Status.APPROVED,
            Reservation.Status.REJECTED,
            Reservation.Status.CANCELLED,
        },
        Reservation.Status.APPROVED: {
            Reservation.Status.ACTIVE,
            Reservation.Status.CANCELLED,
        },
        Reservation.Status.ACTIVE: {
            Reservation.Status.COMPLETED,
        },
        Reservation.Status.REJECTED: set(),
        Reservation.Status.CANCELLED: set(),
        Reservation.Status.COMPLETED: set(),
        Reservation.Status.INTERRUPTED: set(),
    }

    current_status = reservation.status
    if new_status not in dict(Reservation.Status.choices):
        messages.error(request, "Statut cible invalide.")
        next_url = request.POST.get("next")
        if next_url:
            return redirect(next_url)
        return redirect("reservation_detail", reservation_id=reservation.id)

    if new_status not in allowed_transitions.get(current_status, set()):
        messages.error(request, "Transition de statut non autorisée.")
        next_url = request.POST.get("next")
        if next_url:
            return redirect(next_url)
        return redirect("reservation_detail", reservation_id=reservation.id)

    old_status = reservation.status

    try:
        if new_status == Reservation.Status.ACTIVE:
            if timezone.localdate() < reservation.start_date:
                messages.error(
                    request,
                    "Impossible d’activer cette réservation : la date de début n’est pas encore atteinte.",
                )
                next_url = request.POST.get("next")
                if next_url:
                    return redirect(next_url)
                return redirect("reservation_detail", reservation_id=reservation.id)

        if new_status == Reservation.Status.CANCELLED:
            if timezone.localdate() >= reservation.start_date:
                messages.error(
                    request,
                    "Impossible d’annuler cette réservation : la période a déjà démarré. "
                    "Utilisez « Interrompre » si elle est active.",
                )
                next_url = request.POST.get("next")
                if next_url:
                    return redirect(next_url)
                return redirect("reservation_detail", reservation_id=reservation.id)

        if new_status in {Reservation.Status.APPROVED, Reservation.Status.ACTIVE}:
            conflicts = Reservation.objects.filter(
                panel_face=reservation.panel_face,
                status__in=Reservation.get_blocking_statuses(),
                start_date__lte=reservation.end_date,
                end_date__gte=reservation.start_date,
            ).exclude(pk=reservation.pk)

            if conflicts.exists():
                messages.error(
                    request,
                    "Impossible de changer le statut : cette face est déjà réservée sur cette période.",
                )
                next_url = request.POST.get("next")
                if next_url:
                    return redirect(next_url)
                return redirect("reservation_detail", reservation_id=reservation.id)

        reservation.status = new_status
        reservation.save()

        ReservationStatusLog.objects.create(
            reservation=reservation,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user,
        )

        if new_status in {
            Reservation.Status.APPROVED,
            Reservation.Status.REJECTED,
            Reservation.Status.CANCELLED,
            Reservation.Status.COMPLETED,
        }:
            send_client_reservation_status_notification(reservation)

        messages.success(
            request,
            f"Le statut de la réservation est maintenant : {reservation.get_status_display()}."
        )
    except ValidationError as exc:
        if hasattr(exc, "message_dict"):
            messages.error(
                request,
                "Impossible de changer le statut : "
                + " | ".join(
                    f"{field}: {', '.join(errors)}"
                    for field, errors in exc.message_dict.items()
                ),
            )
        else:
            messages.error(
                request,
                "Impossible de changer le statut : "
                + " | ".join(exc.messages),
            )

    next_url = request.POST.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("reservation_detail", reservation_id=reservation.id)

@login_required
def reservation_interrupt(request, reservation_id):
    if request.method != "POST":
        raise Http404("Invalid method.")

    reservation = get_agency_scoped_reservation_or_404(request.user, reservation_id)

    if reservation.status != Reservation.Status.ACTIVE:
        messages.error(request, "Seule une réservation active peut être interrompue.")
        return redirect("reservation_detail", reservation_id=reservation.id)

    interrupted_at_str = request.POST.get("interrupted_at", "").strip()
    interrupted_reason = request.POST.get("interrupted_reason", "").strip()
    interrupted_comment = request.POST.get("interrupted_comment", "").strip()

    try:
        interrupted_at = date.fromisoformat(interrupted_at_str)
    except ValueError:
        messages.error(request, "Date d’interruption invalide.")
        return redirect("reservation_detail", reservation_id=reservation.id)

    old_status = reservation.status

    try:
        reservation.status = Reservation.Status.INTERRUPTED
        reservation.interrupted_at = interrupted_at
        reservation.interrupted_reason = interrupted_reason
        reservation.interrupted_comment = interrupted_comment
        reservation.save()

        ReservationStatusLog.objects.create(
            reservation=reservation,
            old_status=old_status,
            new_status=Reservation.Status.INTERRUPTED,
            changed_by=request.user,
            note=f"Motif : {reservation.get_interrupted_reason_display()}. {interrupted_comment}".strip(),
        )

        send_client_reservation_status_notification(reservation)

        messages.success(request, "La réservation a été interrompue.")
    except ValidationError as exc:
        if hasattr(exc, "message_dict"):
            messages.error(
                request,
                "Impossible d’interrompre : "
                + " | ".join(
                    f"{field}: {', '.join(errors)}"
                    for field, errors in exc.message_dict.items()
                ),
            )
        else:
            messages.error(request, "Impossible d’interrompre : " + " | ".join(exc.messages))

    return redirect("reservation_detail", reservation_id=reservation.id)

@login_required
def reservation_tax_line_create(request, reservation_id):
    if request.method != "POST":
        raise Http404("Invalid method.")

    reservation = get_agency_scoped_reservation_or_404(request.user, reservation_id)
    form = ReservationTaxLineForm(request.POST)

    if form.is_valid():
        tax_line = form.save(commit=False)
        tax_line.reservation = reservation
        tax_line.order = reservation.tax_lines.count()
        tax_line.save()
        messages.success(request, "Ligne ajoutée.")
    else:
        messages.error(
            request,
            "Impossible d’ajouter la ligne : "
            + " | ".join(f"{f}: {', '.join(e)}" for f, e in form.errors.items()),
        )

    return redirect("reservation_detail", reservation_id=reservation.id)

@login_required
def reservation_tax_line_update(request, reservation_id, line_id):
    if request.method != "POST":
        raise Http404("Invalid method.")

    reservation = get_agency_scoped_reservation_or_404(request.user, reservation_id)
    tax_line = get_object_or_404(ReservationTaxLine, pk=line_id, reservation=reservation)

    form = ReservationTaxLineForm(request.POST, instance=tax_line)
    if form.is_valid():
        form.save()
        messages.success(request, "Ligne mise à jour.")
    else:
        messages.error(
            request,
            "Impossible de mettre à jour la ligne : "
            + " | ".join(f"{f}: {', '.join(e)}" for f, e in form.errors.items()),
        )

    return redirect("reservation_detail", reservation_id=reservation.id)


@login_required
def reservation_tax_line_delete(request, reservation_id, line_id):
    if request.method != "POST":
        raise Http404("Invalid method.")

    reservation = get_agency_scoped_reservation_or_404(request.user, reservation_id)
    tax_line = get_object_or_404(ReservationTaxLine, pk=line_id, reservation=reservation)
    tax_line.delete()
    messages.success(request, "Ligne supprimée.")

    return redirect("reservation_detail", reservation_id=reservation.id)


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


def geographic_units_api(request):
    """
    Retourne les unités géographiques enfants d'un niveau donné.
    - Avec ?country=XX : retourne les unités de niveau 1 (racines) de ce pays.
    - Avec ?parent=<id> : retourne les enfants directs de cette unité.
    """
    country_code = request.GET.get("country", "").strip()
    parent_id = request.GET.get("parent", "").strip()

    if parent_id:
        try:
            parent = GeographicUnit.objects.select_related("level").get(pk=parent_id)
        except (GeographicUnit.DoesNotExist, ValueError):
            return JsonResponse({"units": [], "level_name": None, "is_leaf_level": True})

        units = parent.children.select_related("level").order_by("name")
        next_level = GeographicLevel.objects.filter(
            country=parent.country, order=parent.level.order + 1
        ).first()

        return JsonResponse(
            {
                "units": [{"id": unit.id, "name": unit.name} for unit in units],
                "level_name": next_level.name if next_level else None,
                "is_leaf_level": next_level is None,
            }
        )

    if country_code:
        try:
            level_1 = GeographicLevel.objects.get(country__code=country_code, order=1)
        except GeographicLevel.DoesNotExist:
            return JsonResponse({"units": [], "level_name": None, "is_leaf_level": True})

        units = GeographicUnit.objects.filter(
            country__code=country_code, level=level_1
        ).order_by("name")

        return JsonResponse(
            {
                "units": [{"id": unit.id, "name": unit.name} for unit in units],
                "level_name": level_1.name,
                "is_leaf_level": GeographicLevel.objects.filter(
                    country__code=country_code, order=2
                ).exists() is False,
            }
        )

    return JsonResponse({"units": [], "level_name": None, "is_leaf_level": True})

def geographic_unit_chain_api(request):
    """Retourne, pour une unité donnée, son pays et la chaîne complète
    (nom + id) de la racine jusqu'à cette unité. Utilisé pour restaurer
    le libellé et le fil d'Ariane sans requêtes séquentielles côté client."""
    unit_id = request.GET.get("unit", "").strip()

    try:
        unit = GeographicUnit.objects.select_related("level", "country").get(pk=unit_id)
    except (GeographicUnit.DoesNotExist, ValueError):
        return JsonResponse({"chain": [], "country_code": None, "country_name": None})

    chain = []
    node = unit
    while node:
        chain.append({"id": node.id, "name": node.name})
        node = node.parent
    chain.reverse()

    return JsonResponse(
        {
            "chain": chain,
            "country_code": unit.country.code,
            "country_name": unit.country.name,
        }
    )

@login_required
def client_list(request):
    clients = (
        Client.objects.annotate(
            reservation_count=Count("reservations", distinct=True),
            active_reservation_count=Count(
                "reservations",
                filter=Q(reservations__status=Reservation.Status.ACTIVE),
                distinct=True,
            ),
            completed_reservation_count=Count(
                "reservations",
                filter=Q(reservations__status=Reservation.Status.COMPLETED),
                distinct=True,
            ),
            last_reservation_date=Max("reservations__created_at"),
        )
        .order_by("contact_name")
    )

    if request.user.role != request.user.Role.SUPER_ADMIN:
        clients = clients.filter(agency=request.user.agency).distinct()

    return render(
        request,
        "core/client_list.html",
        {
            "clients": clients,
        },
    )


@login_required
def client_detail(request, client_id):
    client = get_object_or_404(Client, pk=client_id)

    reservations = client.reservations.select_related(
        "agency",
        "panel_face",
        "panel_face__panel",
    ).order_by("-created_at")

    if request.user.role != request.user.Role.SUPER_ADMIN:
        if client.agency != request.user.agency:
            raise Http404("Client introuvable pour cette agence.")

    stats = {
        "total": reservations.count(),
        "active": reservations.filter(status=Reservation.Status.ACTIVE).count(),
        "completed": reservations.filter(status=Reservation.Status.COMPLETED).count(),
        "pending": reservations.filter(status=Reservation.Status.PENDING).count(),
    }

    return render(
        request,
        "core/client_detail.html",
        {
            "client_obj": client,
            "reservations": reservations,
            "stats": stats,
        },
    )


@login_required
def client_create(request):
    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":
        form = ClientForm(request.POST, user=request.user)

        if form.is_valid():
            client = form.save(commit=False)

            if request.user.role != request.user.Role.SUPER_ADMIN:
                client.agency = request.user.agency

            client.save()

            messages.success(request, "Client créé avec succès.")

            if next_url:
                separator = "&" if "?" in next_url else "?"
                return redirect(f"{next_url}{separator}client_id={client.id}")

            return redirect("client_detail", client_id=client.id)
    else:
        form = ClientForm(user=request.user)

    return render(
        request,
        "core/client_form.html",
        {
            "form": form,
            "page_title": "Créer un client",
            "submit_label": "Créer le client",
            "next_url": next_url,
        },
    )


@login_required
def client_update(request, client_id):
    client = get_object_or_404(Client, pk=client_id)

    if request.user.role != request.user.Role.SUPER_ADMIN:
        if client.agency != request.user.agency:
            raise Http404("Client introuvable pour cette agence.")

    if request.method == "POST":
        form = ClientForm(request.POST, instance=client, user=request.user)
        if form.is_valid():
            client = form.save()
            messages.success(request, "Client mis à jour avec succès.")
            return redirect("client_detail", client_id=client.id)
    else:
        form = ClientForm(instance=client)

    return render(
        request,
        "core/client_form.html",
        {
            "form": form,
            "client_obj": client,
            "page_title": "Modifier un client",
            "submit_label": "Mettre à jour",
        },
    )

def is_super_admin(user):
    return user.is_authenticated and user.role == user.Role.SUPER_ADMIN


def is_agency_admin_or_super(user):
    return user.is_authenticated and user.role in {
        user.Role.SUPER_ADMIN,
        user.Role.AGENCY_ADMIN,
    }


@login_required
def agency_list(request):
    if not is_super_admin(request.user):
        raise Http404("Accès réservé aux super administrateurs.")

    agencies = Agency.objects.select_related("geographic_unit").all()
    return render(request, "core/agency_list.html", {"agencies": agencies})


@login_required
def agency_create(request):
    if not is_super_admin(request.user):
        raise Http404("Accès réservé aux super administrateurs.")

    if request.method == "POST":
        form = AgencyForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Régie créée avec succès.")
            return redirect("agency_list")
    else:
        form = AgencyForm()

    return render(
        request,
        "core/agency_form.html",
        {
            "form": form,
            "agency": None,
            "page_title": "Créer une régie",
            "submit_label": "Créer la régie",
        },
    )


@login_required
def agency_update(request, agency_id):
    if not is_super_admin(request.user):
        raise Http404("Accès réservé aux super administrateurs.")

    agency = get_object_or_404(Agency, pk=agency_id)

    if request.method == "POST":
        form = AgencyForm(request.POST, request.FILES, instance=agency)
        if form.is_valid():
            form.save()
            messages.success(request, "Régie mise à jour avec succès.")
            return redirect("agency_list")
    else:
        form = AgencyForm(instance=agency)

    return render(
        request,
        "core/agency_form.html",
        {
            "form": form,
            "agency": agency,
            "page_title": "Modifier la régie",
            "submit_label": "Mettre à jour",
        },
    )


@login_required
def agency_profile(request):
    if not is_agency_admin_or_super(request.user):
        raise Http404("Accès réservé aux administrateurs de régie.")

    if not request.user.agency:
        messages.error(request, "Aucune régie n'est associée à votre compte.")
        return redirect("dashboard")

    agency = request.user.agency

    if request.method == "POST":
        form = AgencyProfileForm(request.POST, request.FILES, instance=agency)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil de la régie mis à jour avec succès.")
            return redirect("agency_profile")
    else:
        form = AgencyProfileForm(instance=agency)

    return render(
        request,
        "core/agency_profile_form.html",
        {
            "form": form,
            "agency": agency,
        },
    )

@login_required
def reservation_invoice_pdf(request, reservation_id):
    reservation = get_agency_scoped_reservation_or_404(request.user, reservation_id)

    allowed_statuses = {
        Reservation.Status.PENDING,
        Reservation.Status.APPROVED,
        Reservation.Status.ACTIVE,
        Reservation.Status.COMPLETED,
        Reservation.Status.INTERRUPTED,
    }

    if reservation.status not in allowed_statuses:
        raise Http404("Document non disponible pour ce statut.")

    is_proforma = not reservation.is_definitive_invoice
    document_word = "proforma" if is_proforma else "facture"

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{document_word}-{reservation.agency.name}-reservation-{reservation.id}.pdf"'
    )

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    margin_x = 50
    y = height - 50

    agency = reservation.agency
    client = reservation.client
    face = reservation.panel_face
    panel = face.panel

    printable_width = width - (2 * margin_x)

    # =========================
    # En-tête agence
    # =========================
    if agency.header_image:
        reader = ImageReader(agency.header_image)
        img_width, img_height = reader.getSize()
        max_header_height = 90

        scale = min(printable_width / img_width, max_header_height / img_height)
        draw_width = img_width * scale
        draw_height = img_height * scale
        draw_x = margin_x + (printable_width - draw_width) / 2

        pdf.drawImage(
            reader,
            draw_x,
            y - draw_height,
            width=draw_width,
            height=draw_height,
            preserveAspectRatio=True,
            mask="auto",
        )
        y -= draw_height + 10
    else:
        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawString(margin_x, y, agency.name.upper())

        y -= 18
        pdf.setFont("Helvetica", 9)

        agency_infos = []
        if getattr(agency, "geographic_unit", None):
            agency_infos.append(agency.geographic_unit.full_path())
        if getattr(agency, "phone", None):
            agency_infos.append(f"Tél. {agency.phone}")
        if getattr(agency, "email", None):
            agency_infos.append(agency.email)

        pdf.drawString(margin_x, y, " | ".join(agency_infos) if agency_infos else "Agence publicitaire")
        y -= 12

        if getattr(agency, "address", None):
            pdf.drawString(margin_x, y, agency.address)
            y -= 12

    # Ligne séparatrice
    y -= 14
    pdf.line(margin_x, y, width - margin_x, y)
    y -= 35

    # =========================
    # Titre facture
    # =========================
    pdf.setFont("Helvetica-Bold", 18)
    title_text = "FACTURE PROFORMA" if is_proforma else "FACTURE"
    pdf.drawString(margin_x, y, title_text)

    pdf.setFont("Helvetica", 10)
    doc_prefix = "PRO" if is_proforma else "FAC"
    doc_label = "Proforma" if is_proforma else "Facture"
    pdf.drawRightString(width - margin_x, y, f"{doc_label} : {doc_prefix}-{reservation.id}")
    y -= 18
    pdf.drawRightString(width - margin_x, y, f"Réservation : #{reservation.id}")
    y -= 18
    pdf.drawRightString(width - margin_x, y, f"Statut : {reservation.get_status_display()}")

    y -= 22
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin_x, y, "Objet : Location d’espace publicitaire")

    y -= 30

    # =========================
    # Bloc client
    # =========================
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin_x, y, "Facturé à")
    y -= 18

    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin_x, y, f"Contact : {client.contact_name}")
    y -= 15
    pdf.drawString(margin_x, y, f"Entreprise : {client.company_name or '—'}")
    y -= 15
    pdf.drawString(margin_x, y, f"Téléphone : {client.phone}")
    y -= 15
    pdf.drawString(margin_x, y, f"Email : {client.email or '—'}")

    y -= 35

    # =========================
    # Informations réservation
    # =========================
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin_x, y, "Détails de la réservation")
    y -= 18

    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin_x, y, f"Panneau : {panel.reference}")
    y -= 15
    pdf.drawString(margin_x, y, f"Face : {face.code}")
    y -= 15
    pdf.drawString(
        margin_x,
        y,
        f"Localisation : {panel.geographic_unit.full_path()}",
    )
    y -= 15
    pdf.drawString(margin_x, y, f"Période : du {reservation.start_date} au {reservation.end_date}")

    y -= 35

    # =========================
    # Tableau prestation
    # =========================
    duration_days = (reservation.end_date - reservation.start_date).days + 1
    duration_months = max(1, duration_days // 30)

    table_x = margin_x
    table_width = width - (2 * margin_x)
    row_height = 24

    pdf.setFont("Helvetica-Bold", 10)
    pdf.rect(table_x, y - row_height, table_width, row_height)
    pdf.drawString(table_x + 8, y - 16, "Désignation")
    pdf.drawString(table_x + 250, y - 16, "Durée")
    pdf.drawString(table_x + 315, y - 16, "Prix mensuel")
    pdf.drawString(table_x + 420, y - 16, "Total")

    y -= row_height

    pdf.setFont("Helvetica", 10)
    pdf.rect(table_x, y - row_height, table_width, row_height)
    pdf.drawString(
        table_x + 8,
        y - 16,
        f"Location face {face.code} - panneau {panel.reference}",
    )
    pdf.drawString(table_x + 250, y - 16, f"{duration_months} mois")
    pdf.drawString(table_x + 315, y - 16, f"{reservation.monthly_price} FCFA")
    pdf.drawString(table_x + 420, y - 16, f"{reservation.total_price} FCFA")

    y -= row_height + 25

    # =========================
    # Taxes / retenues (facture définitive uniquement)
    # =========================
    tax_lines = [] if is_proforma else reservation.get_computed_tax_lines()

    total_box_width = 220
    total_box_x = width - margin_x - total_box_width

    if tax_lines:
        pdf.setFont("Helvetica", 9)
        for line in tax_lines:
            sign = "+" if line["line_type"] == "addition" else "-"
            label_text = f"{line['label']} ({line['detail']})"
            pdf.drawString(total_box_x, y, label_text)
            pdf.drawRightString(total_box_x + total_box_width, y, f"{sign} {line['amount']} FCFA")
            y -= 14
        y -= 10

        # =========================
        # Total
        # =========================
    final_amount = reservation.net_payable_amount if tax_lines else reservation.total_price

    pdf.rect(total_box_x, y - 42, total_box_width, 42)
    pdf.setFont("Helvetica-Bold", 11)
    if is_proforma:
        total_label = "MONTANT ESTIMÉ"
    elif tax_lines:
        total_label = "NET À PAYER"
    else:
        total_label = "TOTAL À PAYER"
    pdf.drawString(total_box_x + 10, y - 16, total_label)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawRightString(total_box_x + total_box_width - 10, y - 32, f"{final_amount} FCFA")

    y -= 75

    # =========================
    # Notes
    # =========================
    pdf.setFont("Helvetica", 9)
    pdf.drawString(
        margin_x,
        y,
        "Cette facture concerne la location de la face publicitaire indiquée ci-dessus.",
    )
    y -= 14
    pdf.drawString(
        margin_x,
        y,
        "La validation définitive dépend des conditions commerciales convenues avec l’agence.",
    )

    # Pied de page
    if agency.footer_image:
        reader = ImageReader(agency.footer_image)
        img_width, img_height = reader.getSize()
        max_footer_height = 90

        scale = min(printable_width / img_width, max_footer_height / img_height)
        draw_width = img_width * scale
        draw_height = img_height * scale
        draw_x = margin_x + (printable_width - draw_width) / 2

        pdf.drawImage(
            reader,
            draw_x,
            15,
            width=draw_width,
            height=draw_height,
            preserveAspectRatio=True,
            mask="auto",
        )
    else:
        pdf.setFont("Helvetica-Oblique", 8)
        pdf.drawCentredString(
            width / 2,
            30,
            "Document généré via PubPanels",
        )

    pdf.showPage()
    pdf.save()

    return response