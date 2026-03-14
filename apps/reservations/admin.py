from django.contrib import admin

from .models import Client, Reservation


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("company_name", "contact_name", "phone", "email", "created_at")
    search_fields = ("company_name", "contact_name", "phone", "email")
    list_filter = ("created_at",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "panel_face",
        "agency",
        "client",
        "source",
        "status",
        "start_date",
        "end_date",
        "monthly_price",
        "total_price",
        "need_design_help",
        "created_at",
    )
    list_filter = ("status", "source", "need_design_help", "agency")
    search_fields = (
        "client__company_name",
        "client__contact_name",
        "client__phone",
        "client__email",
        "panel_face__panel__reference",
    )
    autocomplete_fields = ("agency", "panel_face", "client", "created_by")