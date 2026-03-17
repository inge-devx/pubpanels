from django import forms

from apps.locations.models import City
from apps.panels.models import Panel
from apps.users.models import User


class PanelForm(forms.ModelForm):
    class Meta:
        model = Panel
        fields = [
            "agency",
            "reference",
            "title",
            "format_category",
            "width_m",
            "height_m",
            "country",
            "city_ref",
            "district",
            "address",
            "latitude",
            "longitude",
            "description",
            "status",
            "is_published",
        ]
        labels = {
            "city_ref": "Ville",
            "width_m": "Largeur (m)",
            "height_m": "Hauteur (m)",
            "format_category": "Catégorie de format",
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if self.user and self.user.role != User.Role.SUPER_ADMIN:
            self.fields["agency"].queryset = self.fields["agency"].queryset.filter(
                id=self.user.agency_id
            )
            self.fields["agency"].initial = self.user.agency

        selected_country = (
            self.data.get("country")
            or self.initial.get("country")
            or getattr(self.instance, "country", None)
            or "BF"
        )

        self.fields["city_ref"].queryset = City.objects.filter(
            country_code=selected_country,
            is_active=True,
        ).order_by("name")

    def save(self, commit=True):
        panel = super().save(commit=False)

        if self.user and self.user.role != User.Role.SUPER_ADMIN:
            panel.agency = self.user.agency

        if panel.city_ref:
            panel.city = panel.city_ref.name

        if commit:
            panel.save()

        return panel