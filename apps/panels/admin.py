from django.contrib import admin

from .models import Panel, PanelFace


class PanelFaceInline(admin.TabularInline):
    model = PanelFace
    extra = 0


@admin.register(Panel)
class PanelAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "agency",
        "format",
        "city",
        "district",
        "status",
        "is_published",
        "created_at",
    )
    list_filter = ("agency", "status", "is_published", "city")
    search_fields = ("reference", "title", "city", "district", "address")
    inlines = [PanelFaceInline]


@admin.register(PanelFace)
class PanelFaceAdmin(admin.ModelAdmin):
    list_display = (
        "panel",
        "code",
        "monthly_price",
        "operational_status",
        "updated_at",
    )
    list_filter = ("code", "operational_status", "panel__agency")
    search_fields = ("panel__reference", "orientation")