from django.contrib import admin

from .models import Agency


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "city",
        "status",
        "commission_rate",
        "alert_days_before_expiry",
        "created_at",
    )
    list_filter = ("status", "city")
    search_fields = ("name", "slug", "email", "phone", "city")
    prepopulated_fields = {"slug": ("name",)}