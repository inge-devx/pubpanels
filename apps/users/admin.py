from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("PubPanels Access", {"fields": ("role", "agency")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("PubPanels Access", {"fields": ("role", "agency")}),
    )
    list_display = ("username", "email", "first_name", "last_name", "role", "agency", "is_staff")
    list_filter = ("role", "agency", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "first_name", "last_name", "email")