from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        AGENCY_ADMIN = "agency_admin", "Agency Admin"
        AGENCY_MANAGER = "agency_manager", "Agency Manager"

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.AGENCY_MANAGER,
    )
    agency = models.ForeignKey(
        "agencies.Agency",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )

    def __str__(self):
        return self.username