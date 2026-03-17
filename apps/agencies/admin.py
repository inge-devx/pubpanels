from django.contrib import admin

from .models import Agency


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country",
        "city_ref",
        "status",
        "commission_rate",
        "alert_days_before_expiry",
        "created_at",
    )
    list_filter = ("country", "status", "city_ref")
    search_fields = ("name", "slug", "email", "phone", "address", "city")
    prepopulated_fields = {"slug": ("name",)}