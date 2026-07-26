from django.contrib import admin
from .models import Country, GeographicLevel, GeographicUnit


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ["name", "code"]
    search_fields = ["name", "code"]


@admin.register(GeographicLevel)
class GeographicLevelAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "order"]
    list_filter = ["country"]
    ordering = ["country", "order"]


@admin.register(GeographicUnit)
class GeographicUnitAdmin(admin.ModelAdmin):
    list_display = ["name", "level", "country", "parent"]
    list_filter = ["country", "level"]
    search_fields = ["name"]
    autocomplete_fields = ["parent"]

    class Media:
        pass