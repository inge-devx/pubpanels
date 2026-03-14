from decimal import Decimal

from django.db import models


class Panel(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        MAINTENANCE = "maintenance", "Maintenance"

    agency = models.ForeignKey(
        "agencies.Agency",
        on_delete=models.CASCADE,
        related_name="panels",
    )
    reference = models.CharField(max_length=100)
    title = models.CharField(max_length=150, blank=True)
    format = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    district = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["reference"]
        constraints = [
            models.UniqueConstraint(
                fields=["agency", "reference"],
                name="unique_panel_reference_per_agency",
            )
        ]
        indexes = [
            models.Index(fields=["agency", "status"]),
            models.Index(fields=["city"]),
            models.Index(fields=["district"]),
            models.Index(fields=["is_published"]),
        ]

    def __str__(self):
        return f"{self.reference} - {self.agency.name}"


class PanelFace(models.Model):
    class FaceCode(models.TextChoices):
        A = "A", "Face A"
        B = "B", "Face B"

    class OperationalStatus(models.TextChoices):
        AVAILABLE = "available", "Available"
        UNAVAILABLE = "unavailable", "Unavailable"
        MAINTENANCE = "maintenance", "Maintenance"

    panel = models.ForeignKey(
        "panels.Panel",
        on_delete=models.CASCADE,
        related_name="faces",
    )
    code = models.CharField(
        max_length=1,
        choices=FaceCode.choices,
    )
    orientation = models.CharField(max_length=100, blank=True)
    monthly_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    operational_status = models.CharField(
        max_length=20,
        choices=OperationalStatus.choices,
        default=OperationalStatus.AVAILABLE,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["panel__reference", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["panel", "code"],
                name="unique_face_code_per_panel",
            )
        ]
        indexes = [
            models.Index(fields=["panel", "code"]),
            models.Index(fields=["operational_status"]),
        ]

    def __str__(self):
        return f"{self.panel.reference} - Face {self.code}"