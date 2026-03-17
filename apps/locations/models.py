from django.db import models

from apps.core.constants import COUNTRY_CHOICES


class City(models.Model):
    country_code = models.CharField(max_length=2, choices=COUNTRY_CHOICES)
    name = models.CharField(max_length=120)
    slug = models.SlugField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["country_code", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["country_code", "name"],
                name="unique_city_name_per_country",
            ),
            models.UniqueConstraint(
                fields=["country_code", "slug"],
                name="unique_city_slug_per_country",
            ),
        ]
        indexes = [
            models.Index(fields=["country_code", "name"]),
            models.Index(fields=["country_code", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.country_code})"