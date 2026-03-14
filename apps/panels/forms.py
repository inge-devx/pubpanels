from django import forms

from apps.panels.models import Panel
from apps.users.models import User


class PanelForm(forms.ModelForm):
    class Meta:
        model = Panel
        fields = [
            "agency",
            "reference",
            "title",
            "format",
            "city",
            "district",
            "address",
            "latitude",
            "longitude",
            "description",
            "status",
            "is_published",
        ]

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if self.user and self.user.role != User.Role.SUPER_ADMIN:
            self.fields["agency"].queryset = self.fields["agency"].queryset.filter(
                id=self.user.agency_id
            )
            self.fields["agency"].initial = self.user.agency

    def save(self, commit=True):
        panel = super().save(commit=False)

        if self.user and self.user.role != User.Role.SUPER_ADMIN:
            panel.agency = self.user.agency

        if commit:
            panel.save()

        return panel
