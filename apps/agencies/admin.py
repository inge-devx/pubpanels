from django.contrib import admin

from .models import Agency


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country",
        "geographic_unit",
        "status",
        "commission_rate",
        "alert_days_before_expiry",
        "created_at",
    )
    list_filter = ("country", "status", "geographic_unit")
    search_fields = ("name", "slug", "email", "phone", "address")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("geographic_unit",)