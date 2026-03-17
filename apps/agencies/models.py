from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.constants import COUNTRY_CHOICES


class Agency(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        SUSPENDED = "suspended", "Suspended"

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(unique=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    country = models.CharField(
        max_length=2,
        choices=COUNTRY_CHOICES,
        default="BF",
    )
    city = models.CharField(max_length=100, blank=True)
    city_ref = models.ForeignKey(
        "locations.City",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agencies",
    )
    address = models.CharField(max_length=255, blank=True)
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

        if self.city_ref and self.city_ref.country_code != self.country:
            raise ValidationError(
                {"city_ref": "The selected city does not belong to the selected country."}
            )

    def save(self, *args, **kwargs):
        if self.city_ref and not self.city:
            self.city = self.city_ref.name
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name