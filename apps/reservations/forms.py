from django import forms

from apps.panels.models import PanelFace

from .models import Reservation


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = [
            "agency",
            "panel_face",
            "client",
            "source",
            "status",
            "start_date",
            "end_date",
            "monthly_price",
            "total_price",
            "need_design_help",
            "notes",
        ]

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if self.user and self.user.role != self.user.Role.SUPER_ADMIN:
            self.fields["agency"].queryset = self.fields["agency"].queryset.filter(
                id=self.user.agency_id
            )
            self.fields["agency"].initial = self.user.agency

            self.fields["panel_face"].queryset = PanelFace.objects.select_related(
                "panel", "panel__agency"
            ).filter(panel__agency=self.user.agency)

    def save(self, commit=True):
        reservation = super().save(commit=False)

        if self.user and self.user.role != self.user.Role.SUPER_ADMIN:
            reservation.agency = self.user.agency

        if commit:
            reservation.save()

        return reservation