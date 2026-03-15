from datetime import timedelta

from django import forms

from apps.panels.models import PanelFace

from .models import Reservation


class ReservationForm(forms.ModelForm):
    duration_months = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Nombre de mois",
        help_text="1 mois commercial = 30 jours.",
    )

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
            "duration_months",
            "monthly_price",
            "total_price",
            "need_design_help",
            "notes",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.HiddenInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        self.fields["end_date"].required = False
        self.fields["monthly_price"].required = False
        self.fields["total_price"].required = False

        if self.instance.pk and self.instance.start_date and self.instance.end_date:
            duration_days = (self.instance.end_date - self.instance.start_date).days + 1
            self.fields["duration_months"].initial = max(1, duration_days // 30)

        if self.user and self.user.role != self.user.Role.SUPER_ADMIN:
            self.fields["agency"].queryset = self.fields["agency"].queryset.filter(
                id=self.user.agency_id
            )
            self.fields["agency"].initial = self.user.agency
            self.fields["panel_face"].queryset = self._get_faces_queryset(self.user.agency_id)
        else:
            selected_agency_id = (
                self.data.get("agency")
                or self.initial.get("agency")
                or getattr(self.instance, "agency_id", None)
            )
            if selected_agency_id:
                self.fields["panel_face"].queryset = self._get_faces_queryset(selected_agency_id)
            else:
                self.fields["panel_face"].queryset = PanelFace.objects.none()

    def _get_faces_queryset(self, agency_id):
        return PanelFace.objects.select_related("panel", "panel__agency").filter(
            panel__agency_id=agency_id,
            operational_status=PanelFace.OperationalStatus.AVAILABLE,
        ).order_by("panel__reference", "code")

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        duration_months = cleaned_data.get("duration_months")
        panel_face = cleaned_data.get("panel_face")
        monthly_price = cleaned_data.get("monthly_price")
        total_price = cleaned_data.get("total_price")

        if self.user and self.user.role != self.user.Role.SUPER_ADMIN:
            cleaned_data["agency"] = self.user.agency

        if start_date and duration_months:
            cleaned_data["end_date"] = start_date + timedelta(days=(30 * duration_months) - 1)

        if panel_face and monthly_price in (None, ""):
            cleaned_data["monthly_price"] = panel_face.monthly_price
            monthly_price = cleaned_data["monthly_price"]

        if monthly_price not in (None, "") and duration_months and total_price in (None, ""):
            cleaned_data["total_price"] = monthly_price * duration_months

        return cleaned_data

    def save(self, commit=True):
        reservation = super().save(commit=False)

        if self.user and self.user.role != self.user.Role.SUPER_ADMIN:
            reservation.agency = self.user.agency

        reservation.end_date = self.cleaned_data["end_date"]
        reservation.monthly_price = self.cleaned_data["monthly_price"]
        reservation.total_price = self.cleaned_data["total_price"]

        if commit:
            reservation.save()

        return reservation