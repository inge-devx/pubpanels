from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.constants import COUNTRY_CHOICES


class Panel(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        MAINTENANCE = "maintenance", "Maintenance"

    class FormatCategory(models.TextChoices):
        SMALL = "small", "Inférieur à 12 m²"
        STANDARD = "standard", "De 12 à moins de 24 m²"
        LARGE = "large", "24 m²"
        XL = "xl", "Supérieur à 24 m²"

    agency = models.ForeignKey(
        "agencies.Agency",
        on_delete=models.CASCADE,
        related_name="panels",
    )
    reference = models.CharField(max_length=100)
    title = models.CharField(max_length=150, blank=True)
    format_category = models.CharField(
        max_length=20,
        choices=FormatCategory.choices,
        default=FormatCategory.STANDARD,
    )
    width_m = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    height_m = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    country = models.CharField(
        max_length=2,
        choices=COUNTRY_CHOICES,
        default="BF",
    )
    city = models.CharField(max_length=100)
    city_ref = models.ForeignKey(
        "locations.City",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="panels",
    )
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
            models.Index(fields=["country"]),
            models.Index(fields=["format_category"]),
            models.Index(fields=["district"]),
            models.Index(fields=["is_published"]),
        ]

    @property
    def area_sqm(self):
        if self.width_m is not None and self.height_m is not None:
            return self.width_m * self.height_m
        return None

    @property
    def formatted_dimensions(self):
        if self.width_m is not None and self.height_m is not None:
            return f"{self.width_m} m x {self.height_m} m"
        return "—"

    def clean(self):
        super().clean()

        if self.city_ref and self.city_ref.country_code != self.country:
            raise ValidationError(
                {"city_ref": "The selected city does not belong to the selected country."}
            )

        if self.width_m is not None and self.width_m <= 0:
            raise ValidationError({"width_m": "Width must be greater than 0."})

        if self.height_m is not None and self.height_m <= 0:
            raise ValidationError({"height_m": "Height must be greater than 0."})

        if (self.width_m is None) != (self.height_m is None):
            raise ValidationError(
                "Width and height must either both be filled or both be empty."
            )

        area = self.area_sqm
        if area is not None:
            if self.format_category == self.FormatCategory.SMALL and area >= Decimal("12"):
                raise ValidationError(
                    {"format_category": "A panel categorized as 'Inférieur à 12 m²' must have an area below 12 m²."}
                )

            if self.format_category == self.FormatCategory.STANDARD and not (
                Decimal("12") <= area < Decimal("24")
            ):
                raise ValidationError(
                    {"format_category": "A panel categorized as 'De 12 à moins de 24 m²' must have an area between 12 m² and less than 24 m²."}
                )

            if self.format_category == self.FormatCategory.LARGE and area != Decimal("24"):
                raise ValidationError(
                    {"format_category": "A panel categorized as '24 m²' must have an area exactly equal to 24 m²."}
                )

            if self.format_category == self.FormatCategory.XL and area <= Decimal("24"):
                raise ValidationError(
                    {"format_category": "A panel categorized as 'Supérieur à 24 m²' must have an area greater than 24 m²."}
                )

    def save(self, *args, **kwargs):
        if self.city_ref and not self.city:
            self.city = self.city_ref.name
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} - {self.agency.name}"


class PanelFace(models.Model):
    MAX_FACES_PER_PANEL = 4

    class FaceCode(models.TextChoices):
        A = "A", "Face A"
        B = "B", "Face B"
        C = "C", "Face C"
        D = "D", "Face D"

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
        ordering = ["panel", "code"]
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

    def clean(self):
        super().clean()

        if not self.panel_id:
            return

        existing_faces = PanelFace.objects.filter(panel=self.panel)
        if self.pk:
            existing_faces = existing_faces.exclude(pk=self.pk)

        if existing_faces.count() >= self.MAX_FACES_PER_PANEL:
            raise ValidationError(
                {
                    "panel": f"A panel cannot have more than {self.MAX_FACES_PER_PANEL} faces."
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.panel.reference} - Face {self.code}"