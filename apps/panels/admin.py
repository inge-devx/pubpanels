from django.contrib import admin

from .models import Panel, PanelFace, PanelFaceImage, PanelImage


class PanelFaceInline(admin.TabularInline):
    model = PanelFace
    extra = 0


class PanelImageInline(admin.TabularInline):
    model = PanelImage
    extra = 0
    fields = ("image", "image_type", "caption", "is_primary", "display_order", "created_at")
    readonly_fields = ("created_at",)


class PanelFaceImageInline(admin.TabularInline):
    model = PanelFaceImage
    extra = 0
    fields = (
        "image",
        "caption",
        "is_primary",
        "is_cover_for_panel",
        "display_order",
        "created_at",
    )
    readonly_fields = ("created_at",)


@admin.register(Panel)
class PanelAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "agency",
        "format_category",
        "formatted_dimensions",
        "country",
        "geographic_unit",
        "status",
        "is_published",
        "created_at",
    )
    list_filter = ("agency", "status", "is_published", "country", "format_category", "geographic_unit")
    search_fields = ("reference", "title", "address")
    autocomplete_fields = ("geographic_unit",)
    inlines = [PanelFaceInline, PanelImageInline]


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
    inlines = [PanelFaceImageInline]


@admin.register(PanelImage)
class PanelImageAdmin(admin.ModelAdmin):
    list_display = (
        "panel",
        "image_type",
        "caption",
        "is_primary",
        "display_order",
        "created_at",
    )
    list_filter = ("image_type", "is_primary", "panel__agency")
    search_fields = ("panel__reference", "caption")


@admin.register(PanelFaceImage)
class PanelFaceImageAdmin(admin.ModelAdmin):
    list_display = (
        "face",
        "caption",
        "is_primary",
        "is_cover_for_panel",
        "display_order",
        "created_at",
    )
    list_filter = ("is_primary", "is_cover_for_panel", "face__panel__agency")
    search_fields = ("face__panel__reference", "face__code", "caption")