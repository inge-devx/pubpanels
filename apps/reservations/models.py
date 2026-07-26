from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Client(models.Model):
    agency = models.ForeignKey(
        "agencies.Agency",
        on_delete=models.CASCADE,
        related_name="clients",
        null=True,
        blank=True,
    )
    company_name = models.CharField(max_length=150, blank=True)
    contact_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    business_sector = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["contact_name"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["phone"]),
            models.Index(fields=["company_name"]),
        ]

    def __str__(self):
        if self.company_name:
            return f"{self.company_name} - {self.contact_name}"
        return self.contact_name


class Reservation(models.Model):
    class Source(models.TextChoices):
        PLATFORM = "platform", "Platform"
        MANUAL = "manual", "Manual"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        INTERRUPTED = "interrupted", "Interrupted"

    class InterruptionReason(models.TextChoices):
        UNPAID = "unpaid", "Non-paiement / impayé client"
        CLIENT_REQUEST = "client_request", "Demande du client"
        TECHNICAL_ISSUE = "technical_issue", "Dégradation ou problème technique du support"
        FORCE_MAJEURE = "force_majeure", "Force majeure"
        REGULATORY_ORDER = "regulatory_order", "Injonction d'une autorité de régulation"
        COMMERCIAL_DISPUTE = "commercial_dispute", "Litige commercial"
        AGENCY_DECISION = "agency_decision", "Décision de la régie"
        OTHER = "other", "Autre"

    agency = models.ForeignKey(
        "agencies.Agency",
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    panel_face = models.ForeignKey(
        "panels.PanelFace",
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    client = models.ForeignKey(
        "reservations.Client",
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.PLATFORM,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    monthly_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    need_design_help = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    interrupted_at = models.DateField(null=True, blank=True)
    interrupted_reason = models.CharField(
        max_length=30,
        choices=InterruptionReason.choices,
        blank=True,
    )
    interrupted_comment = models.TextField(blank=True)

    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_reservations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agency", "status"]),
            models.Index(fields=["panel_face", "status"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["source"]),
        ]

    @classmethod
    def get_blocking_statuses(cls):
        return [cls.Status.APPROVED, cls.Status.ACTIVE]

    @property
    def is_definitive_invoice(self):
        return self.status in {
            self.Status.APPROVED,
            self.Status.ACTIVE,
            self.Status.COMPLETED,
            self.Status.INTERRUPTED,
        }

    def get_computed_tax_lines(self):
        lines = []
        for tax_line in self.tax_lines.all():
            amount = tax_line.compute_amount(self.total_price)
            signed_amount = amount if tax_line.line_type == tax_line.LineType.ADDITION else -amount

            if tax_line.computation_mode == tax_line.ComputationMode.PERCENTAGE:
                detail = f"{tax_line.rate_percent} %"
            else:
                detail = "montant fixe"

            lines.append({
                "label": tax_line.label,
                "detail": detail,
                "line_type": tax_line.line_type,
                "amount": amount,
                "signed_amount": signed_amount,
            })
        return lines

    @property
    def net_payable_amount(self):
        total = self.total_price
        for line in self.get_computed_tax_lines():
            total += line["signed_amount"]
        return total.quantize(Decimal("0.01"))

    def get_overlapping_blocking_reservations(self):
        if not self.panel_face_id or not self.start_date or not self.end_date:
            return Reservation.objects.none()

        overlapping = Reservation.objects.filter(
            panel_face=self.panel_face,
            status__in=self.get_blocking_statuses(),
            start_date__lte=self.end_date,
            end_date__gte=self.start_date,
        )

        if self.pk:
            overlapping = overlapping.exclude(pk=self.pk)

        return overlapping

    def clean(self):
        super().clean()

        if self.pk:
            old = Reservation.objects.get(pk=self.pk)

            locked_statuses = {
                self.Status.APPROVED,
                self.Status.ACTIVE,
                self.Status.COMPLETED,
                self.Status.INTERRUPTED,
            }

            if old.status in locked_statuses:
                if (
                        old.start_date != self.start_date
                        or old.end_date != self.end_date
                        or old.panel_face_id != self.panel_face_id
                        or old.monthly_price != self.monthly_price
                ):
                    raise ValidationError(
                        "Impossible de modifier une réservation validée."
                    )

        if self.panel_face_id and self.agency_id:
            panel_agency_id = self.panel_face.panel.agency_id
            if panel_agency_id != self.agency_id:
                raise ValidationError(
                    {"agency": "The selected panel face does not belong to the selected agency."}
                )

        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError(
                    {"end_date": "End date must be greater than or equal to start date."}
                )

            duration_days = (self.end_date - self.start_date).days + 1
            if duration_days < 30:
                raise ValidationError(
                    {"end_date": "Reservation duration must be at least 30 days."}
                )

        if (
            self.status in self.get_blocking_statuses()
            and self.panel_face_id
            and self.start_date
            and self.end_date
        ):
            overlapping = self.get_overlapping_blocking_reservations()
            if overlapping.exists():
                raise ValidationError(
                    "This panel face is already reserved for the selected period."
                )

        if self.status == self.Status.INTERRUPTED:
            if not self.interrupted_at:
                raise ValidationError(
                    {"interrupted_at": "La date d'interruption est obligatoire."}
                )
            if not self.interrupted_reason:
                raise ValidationError(
                    {"interrupted_reason": "Le motif d'interruption est obligatoire."}
                )
            if self.start_date and self.interrupted_at < self.start_date:
                raise ValidationError(
                    {"interrupted_at": "La date d'interruption ne peut pas être antérieure à la date de début."}
                )
            if self.interrupted_at > timezone.localdate():
                raise ValidationError(
                    {"interrupted_at": "La date d'interruption ne peut pas être dans le futur."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.panel_face} | {self.start_date} -> {self.end_date}"

class ReservationStatusLog(models.Model):
    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.CASCADE,
        related_name="status_logs",
    )
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reservation_id} : {self.old_status} -> {self.new_status}"

class ReservationTaxLine(models.Model):
    class LineType(models.TextChoices):
        ADDITION = "addition", "Ajout (taxe facturée en plus au client)"
        DEDUCTION = "deduction", "Retenue (déduite du montant net à percevoir)"

    class ComputationMode(models.TextChoices):
        PERCENTAGE = "percentage", "Pourcentage du montant"
        FIXED = "fixed", "Montant fixe"

    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.CASCADE,
        related_name="tax_lines",
    )
    label = models.CharField(max_length=100)
    line_type = models.CharField(max_length=20, choices=LineType.choices)
    computation_mode = models.CharField(max_length=20, choices=ComputationMode.choices)
    rate_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    fixed_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]

    def clean(self):
        super().clean()
        if self.computation_mode == self.ComputationMode.PERCENTAGE and self.rate_percent is None:
            raise ValidationError({"rate_percent": "Le taux est obligatoire pour un calcul en pourcentage."})
        if self.computation_mode == self.ComputationMode.FIXED and self.fixed_amount is None:
            raise ValidationError({"fixed_amount": "Le montant est obligatoire pour un calcul en montant fixe."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def compute_amount(self, base_amount):
        if self.computation_mode == self.ComputationMode.PERCENTAGE:
            return (base_amount * self.rate_percent / Decimal("100")).quantize(Decimal("0.01"))
        return self.fixed_amount

    @property
    def amount_display(self):
        return self.compute_amount(self.reservation.total_price)

    def __str__(self):
        return f"{self.reservation_id} : {self.label}"