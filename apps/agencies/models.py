from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.constants import COUNTRY_CHOICES

HEADER_IMAGE_MIN_RATIO = 3.0
HEADER_IMAGE_MAX_RATIO = 8.0
FOOTER_IMAGE_MIN_RATIO = 5.0
FOOTER_IMAGE_MAX_RATIO = 12.0

class Agency(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        SUSPENDED = "suspended", "Suspended"

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(unique=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    geographic_unit = models.ForeignKey(
        "geography.GeographicUnit",
        on_delete=models.PROTECT,
        related_name="agencies",
    )
    country = models.CharField(
        max_length=2,
        choices=COUNTRY_CHOICES,
        default="BF",
    )
    address = models.CharField(max_length=255, blank=True)

    header_image = models.ImageField(
        upload_to="agencies/headers/",
        null=True,
        blank=True,
        help_text="Bandeau d'en-tête pour les documents PDF (PNG/JPG, format large recommandé).",
    )
    footer_image = models.ImageField(
        upload_to="agencies/footers/",
        null=True,
        blank=True,
        help_text="Bandeau de pied de page pour les documents PDF (PNG/JPG, format large recommandé).",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
        help_text="Commission rate in percent for platform-acquired new clients.",
    )
    alert_days_before_expiry = models.PositiveIntegerField(default=7)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def clean(self):
        super().clean()
        if self.geographic_unit_id and self.geographic_unit.country.code != self.country:
            raise ValidationError(
                {"geographic_unit": "L'unité géographique ne correspond pas au pays de la régie."}
            )

        if self.header_image:
            ratio = self.header_image.width / self.header_image.height
            if not (HEADER_IMAGE_MIN_RATIO <= ratio <= HEADER_IMAGE_MAX_RATIO):
                raise ValidationError(
                    {
                        "header_image": (
                            f"Format d'image inadapté (ratio largeur/hauteur {ratio:.1f}). "
                            f"Utilisez une bannière large, ratio attendu entre "
                            f"{HEADER_IMAGE_MIN_RATIO:.0f}:1 et {HEADER_IMAGE_MAX_RATIO:.0f}:1 "
                            f"(ex. 1200x200 px)."
                        )
                    }
                )

        if self.footer_image:
            ratio = self.footer_image.width / self.footer_image.height
            if not (FOOTER_IMAGE_MIN_RATIO <= ratio <= FOOTER_IMAGE_MAX_RATIO):
                raise ValidationError(
                    {
                        "footer_image": (
                            f"Format d'image inadapté (ratio largeur/hauteur {ratio:.1f}). "
                            f"Utilisez une bannière fine, ratio attendu entre "
                            f"{FOOTER_IMAGE_MIN_RATIO:.0f}:1 et {FOOTER_IMAGE_MAX_RATIO:.0f}:1 "
                            f"(ex. 1200x150 px)."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name