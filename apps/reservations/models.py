from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class Client(models.Model):
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

    @property
    def blocking_statuses(self):
        return [self.Status.APPROVED, self.Status.ACTIVE]

    def clean(self):
        super().clean()

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
            self.status in self.blocking_statuses
            and self.panel_face_id
            and self.start_date
            and self.end_date
        ):
            overlapping = Reservation.objects.filter(
                panel_face=self.panel_face,
                status__in=self.blocking_statuses,
                start_date__lte=self.end_date,
                end_date__gte=self.start_date,
            )

            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)

            if overlapping.exists():
                raise ValidationError(
                    "This panel face is already reserved for the selected period."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.panel_face} | {self.start_date} -> {self.end_date}"