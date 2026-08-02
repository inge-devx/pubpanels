from django.contrib.gis.db import models
from decimal import Decimal
from django.utils import timezone

from django.core.exceptions import ValidationError



from apps.core.constants import COUNTRY_CHOICES


def panel_image_upload_to(instance, filename):
    return f"panels/{instance.panel_id}/{filename}"


def panel_face_image_upload_to(instance, filename):
    return f"panels/{instance.face.panel_id}/faces/{instance.face_id}/{filename}"


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
    geographic_unit = models.ForeignKey(
        "geography.GeographicUnit",
        on_delete=models.PROTECT,
        related_name="panels",
    )
    address = models.CharField(max_length=255, blank=True)

    location = models.PointField(srid=4326, null=True, blank=True)

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
            models.Index(fields=["geographic_unit"]),
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

    @property
    def google_maps_url(self):
        if self.location:
            # Dans GeoDjango, location.y est TOUJOURS la Latitude
            # et location.x est TOUJOURS la Longitude
            lat = self.location.y
            lng = self.location.x

            # On génère une URL de recherche universelle Google Maps

            return f"https://www.google.com/maps?q={lat},{lng}"
        return ""

    @property
    def cover_image(self):
        for face in self.faces.all():
            img = face.images.filter(is_cover_for_panel=True).first()
            if img:
                return img

        for face in self.faces.all():
            img = face.images.filter(is_primary=True).first()
            if img:
                return img

        return None

    def clean(self):
        super().clean()

        if self.geographic_unit_id and self.geographic_unit.country.code != self.country:
            raise ValidationError(
                {"geographic_unit": "The selected geographic unit does not belong to the selected country."}
            )

        if self.width_m is not None and self.width_m <= 0:
            raise ValidationError({"width_m": "Width must be greater than 0."})

        if self.height_m is not None and self.height_m <= 0:
            raise ValidationError({"height_m": "Height must be greater than 0."})

        if (self.width_m is None) != (self.height_m is None):
            raise ValidationError(
                "Width and height must either both be filled or both be empty."
            )

        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError(
                "Latitude and longitude must either both be filled or both be empty."
            )

        area = self.area_sqm
        if area is not None:
            if self.format_category == self.FormatCategory.SMALL and area >= Decimal("12"):
                raise ValidationError(
                    {
                        "format_category": (
                            "A panel categorized as 'Inférieur à 12 m²' "
                            "must have an area below 12 m²."
                        )
                    }
                )

            if self.format_category == self.FormatCategory.STANDARD and not (
                Decimal("12") <= area < Decimal("24")
            ):
                raise ValidationError(
                    {
                        "format_category": (
                            "A panel categorized as 'De 12 à moins de 24 m²' "
                            "must have an area between 12 m² and less than 24 m²."
                        )
                    }
                )

            if self.format_category == self.FormatCategory.LARGE and area != Decimal("24"):
                raise ValidationError(
                    {
                        "format_category": (
                            "A panel categorized as '24 m²' must have an area exactly equal to 24 m²."
                        )
                    }
                )

            if self.format_category == self.FormatCategory.XL and area <= Decimal("24"):
                raise ValidationError(
                    {
                        "format_category": (
                            "A panel categorized as 'Supérieur à 24 m²' "
                            "must have an area greater than 24 m²."
                        )
                    }
                )

    def save(self, *args, **kwargs):
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

    def has_blocking_reservation_for_period(self, start_date=None, end_date=None):
        """
        Retourne True si la face possède une réservation bloquante
        (approved ou active) sur la période donnée.
        Si aucune période n'est fournie, on évalue la disponibilité actuelle
        selon une règle conservatrice : toute réservation bloquante existante
        rend la face indisponible dans le public.
        """
        from apps.reservations.models import Reservation

        blocking_qs = self.reservations.filter(
            status__in=Reservation.get_blocking_statuses()
        )

        if start_date is None or end_date is None:
            return blocking_qs.exists()

        return blocking_qs.filter(
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exists()

    def is_available_for_period(self, start_date=None, end_date=None):
        """
        Une face est réellement disponible si :
        - son statut opérationnel est AVAILABLE
        - elle n'a aucune réservation bloquante sur la période
        """
        if self.operational_status != self.OperationalStatus.AVAILABLE:
            return False

        return not self.has_blocking_reservation_for_period(start_date, end_date)


class PanelImage(models.Model):
    class ImageType(models.TextChoices):
        FACE = "face", "Face du panneau"
        ENVIRONMENT = "environment", "Environnement"
        OTHER = "other", "Autre"

    panel = models.ForeignKey(
        "panels.Panel",
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to=panel_image_upload_to)
    image_type = models.CharField(
        max_length=20,
        choices=ImageType.choices,
        default=ImageType.OTHER,
    )
    caption = models.CharField(max_length=150, blank=True)
    is_primary = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "id"]
        indexes = [
            models.Index(fields=["panel", "image_type"]),
            models.Index(fields=["panel", "is_primary"]),
        ]

    def clean(self):
        super().clean()

        if self.is_primary and self.panel_id:
            existing_primary = PanelImage.objects.filter(
                panel_id=self.panel_id,
                is_primary=True,
            )
            if self.pk:
                existing_primary = existing_primary.exclude(pk=self.pk)

            if existing_primary.exists():
                raise ValidationError(
                    {"is_primary": "Only one primary image is allowed per panel."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.panel.reference} - {self.get_image_type_display()}"


class PanelFaceImage(models.Model):
    face = models.ForeignKey(
        "panels.PanelFace",
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to=panel_face_image_upload_to)
    caption = models.CharField(max_length=150, blank=True)
    is_primary = models.BooleanField(default=False)
    is_cover_for_panel = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "id"]
        indexes = [
            models.Index(fields=["face", "is_primary"]),
            models.Index(fields=["face", "is_cover_for_panel"]),
        ]

    def clean(self):
        super().clean()

        if self.is_primary and self.face_id:
            existing_primary = PanelFaceImage.objects.filter(
                face_id=self.face_id,
                is_primary=True,
            )
            if self.pk:
                existing_primary = existing_primary.exclude(pk=self.pk)

            if existing_primary.exists():
                raise ValidationError(
                    {"is_primary": "Only one primary image is allowed per face."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.face.panel.reference} - Face {self.face.code}"


class PanelImportBatch(models.Model):
    class Status(models.TextChoices):
        CONFIGURING = "configuring", "Configuration"
        IN_PROGRESS = "in_progress", "En cours"
        COMPLETED = "completed", "Terminé"

    agency = models.ForeignKey(
        "agencies.Agency",
        on_delete=models.CASCADE,
        related_name="import_batches",
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    source_filename = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CONFIGURING,
    )
    raw_grid = models.JSONField(null=True, blank=True)
    reference_prefix = models.CharField(max_length=20, blank=True)
    next_reference_number = models.PositiveIntegerField(default=1)
    last_geographic_unit = models.ForeignKey(
        "geography.GeographicUnit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def total_rows(self):
        return self.rows.count()

    @property
    def processed_rows(self):
        return self.rows.exclude(status=PanelImportRow.Status.PENDING).count()

    @property
    def progress_percent(self):
        total = self.total_rows
        if total == 0:
            return 100
        return round((self.processed_rows / total) * 100)

    def __str__(self):
        return f"Import {self.agency.name} - {self.created_at:%d/%m/%Y}"


class PanelImportRow(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        CREATED = "created", "Créée"
        SKIPPED = "skipped", "Ignorée"

    batch = models.ForeignKey(
        "panels.PanelImportBatch",
        on_delete=models.CASCADE,
        related_name="rows",
    )
    row_index = models.PositiveIntegerField()
    headers = models.JSONField(default=list, blank=True)
    values = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_panel = models.ForeignKey(
        "panels.Panel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["row_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "row_index"],
                name="unique_row_index_per_batch",
            )
        ]

    def cells(self):
        pairs = []
        for i, header in enumerate(self.headers):
            cell = self.values[i] if i < len(self.values) else {"v": "", "bg": None}
            pairs.append({"header": header or f"Colonne {i + 1}", "value": cell.get("v", ""), "bg": cell.get("bg")})
        return pairs

    def field_pairs(self):
        pairs = []
        for i, header in enumerate(self.headers):
            cell = self.values[i] if i < len(self.values) else {"v": "", "bg": None}
            pairs.append({
                "label": header or f"Colonne {i + 1}",
                "value": cell.get("v", ""),
                "bg": cell.get("bg"),
            })
        return pairs

    def __str__(self):
        return f"{self.batch_id} - ligne {self.row_index}"