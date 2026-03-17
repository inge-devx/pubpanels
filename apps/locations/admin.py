from django.contrib import admin

from .models import City


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "country_code", "slug", "is_active", "created_at")
    list_filter = ("country_code", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}