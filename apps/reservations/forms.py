from datetime import timedelta

from django import forms

from apps.panels.models import PanelFace
from apps.users.models import User

from .models import Reservation
from django.utils import timezone


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
            "start_date",
            "end_date",
            "duration_months",
            "monthly_price",
            "total_price",
            "need_design_help",
            "notes",
        ]
        widgets = {
            "start_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "end_date": forms.HiddenInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        self.fields["start_date"].input_formats = ["%Y-%m-%d"]
        self.fields["end_date"].required = False
        self.fields["monthly_price"].required = False
        self.fields["total_price"].required = False

        if self.user and self.user.role != User.Role.SUPER_ADMIN:
            self.fields["agency"].queryset = self.fields["agency"].queryset.filter(
                id=self.user.agency_id
            )
            self.fields["agency"].initial = self.user.agency

            self.fields["panel_face"].queryset = PanelFace.objects.select_related(
                "panel", "panel__agency"
            ).filter(panel__agency=self.user.agency)
        else:
            selected_agency = (
                self.data.get("agency")
                or self.initial.get("agency")
                or getattr(self.instance, "agency_id", None)
            )

            if selected_agency:
                self.fields["panel_face"].queryset = PanelFace.objects.select_related(
                    "panel", "panel__agency"
                ).filter(panel__agency_id=selected_agency)
            else:
                self.fields["panel_face"].queryset = PanelFace.objects.select_related(
                    "panel", "panel__agency"
                ).all()

    def clean(self):
        cleaned_data = super().clean()

        agency = cleaned_data.get("agency")
        panel_face = cleaned_data.get("panel_face")
        start_date = cleaned_data.get("start_date")
        duration_months = cleaned_data.get("duration_months")
        monthly_price = cleaned_data.get("monthly_price")

        # 🔒 SÉCURITÉ 1 : On force l'agence de la réservation à être celle de l'utilisateur connecté
        # (Pour éviter qu'un commercial ne soumette une réservation au nom d'une autre agence)
        if self.user and self.user.role != User.Role.SUPER_ADMIN:
            agency = self.user.agency
            cleaned_data["agency"] = agency

        if agency and panel_face and panel_face.panel.agency_id != agency.id:
            self.add_error("panel_face", "La face sélectionnée n’appartient pas à votre agence.")

        # --- Le reste de votre validation existante reste inchangé ---
        if start_date and start_date < timezone.localdate():
            self.add_error("start_date", "La date de début ne peut pas être antérieure à aujourd’hui.")

        if start_date and duration_months:
            cleaned_data["end_date"] = start_date + timedelta(days=(30 * duration_months) - 1)
            end_date = cleaned_data["end_date"]

            # 🔒 PROTECTION : Détection des chevauchements de dates
            if panel_face:
                # On cherche s'il existe des réservations actives (non annulées/rejetées) sur cette même face et cette période
                conflits = Reservation.objects.filter(
                    panel_face=panel_face,
                    start_date__lte=end_date,
                    end_date__ge=start_date
                ).exclude(
                    status__in=["rejected", "cancelled"]  # On exclut les réservations abandonnées
                )

                if conflits.exists():
                    self.add_error(
                        "start_date",
                        "Ce panneau est déjà réservé sur tout ou partie de la période sélectionnée."
                    )

        if panel_face:
            if monthly_price in (None, ""):
                cleaned_data["monthly_price"] = panel_face.monthly_price
            else:
                cleaned_data["monthly_price"] = monthly_price

            if duration_months:
                cleaned_data["total_price"] = cleaned_data["monthly_price"] * duration_months

        return cleaned_data

    def save(self, commit=True):
        reservation = super().save(commit=False)

        reservation.end_date = self.cleaned_data["end_date"]
        reservation.monthly_price = self.cleaned_data["monthly_price"]
        reservation.total_price = self.cleaned_data["total_price"]

        if self.user and self.user.role != User.Role.SUPER_ADMIN:
            reservation.agency = self.user.agency

        if commit:
            reservation.save()

        return reservation


class ReservationUpdateForm(forms.ModelForm):
    duration_months = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Nombre de mois",
        help_text="1 mois commercial = 30 jours.",
    )

    class Meta:
        model = Reservation
        fields = [
            "panel_face",
            "client",
            "start_date",
            "end_date",
            "duration_months",
            "monthly_price",
            "total_price",
            "need_design_help",
            "notes",
        ]
        widgets = {
            "start_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
            "end_date": forms.HiddenInput(),
        }

    def __init__(self, *args, user=None, reservation=None, **kwargs):
        self.user = user
        self.reservation = reservation or kwargs.get("instance")
        super().__init__(*args, **kwargs)

        self.fields["start_date"].input_formats = ["%Y-%m-%d"]
        self.fields["end_date"].required = False
        self.fields["monthly_price"].required = False
        self.fields["total_price"].required = False

        if self.instance.pk:
            if self.instance.start_date:
                self.initial["start_date"] = self.instance.start_date.strftime("%Y-%m-%d")

            if self.instance.end_date:
                self.initial["end_date"] = self.instance.end_date

            if self.instance.start_date and self.instance.end_date:
                duration_days = (self.instance.end_date - self.instance.start_date).days + 1
                self.fields["duration_months"].initial = max(1, duration_days // 30)

        if self.user and self.user.role != self.user.Role.SUPER_ADMIN:
            self.fields["panel_face"].queryset = PanelFace.objects.select_related(
                "panel", "panel__agency"
            ).filter(panel__agency=self.user.agency)
        else:
            self.fields["panel_face"].queryset = PanelFace.objects.select_related(
                "panel", "panel__agency"
            ).all()

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        duration_months = cleaned_data.get("duration_months")
        panel_face = cleaned_data.get("panel_face")
        monthly_price = cleaned_data.get("monthly_price")

        # 🔒 SÉCURITÉ 2 : Empêcher la modification si la face appartient à un concurrent
        if self.user and self.user.role != User.Role.SUPER_ADMIN:
            if panel_face and panel_face.panel.agency_id != self.user.agency_id:
                self.add_error("panel_face", "Vous n'avez pas l'autorisation d'assigner un panneau d'une autre agence.")

        # --- Le reste de votre validation existante reste inchangé ---
        if start_date and start_date < timezone.localdate():
            self.add_error("start_date", "La date de début ne peut pas être antérieure à aujourd’hui.")

        if start_date and duration_months:
            cleaned_data["end_date"] = start_date + timedelta(days=(30 * duration_months) - 1)
            end_date = cleaned_data["end_date"]

            # 🔒 PROTECTION : Détection des chevauchements pour la mise à jour
            if panel_face and self.instance.pk:
                conflits = Reservation.objects.filter(
                    panel_face=panel_face,
                    start_date__lte=end_date,
                    end_date__ge=start_date
                ).exclude(
                    pk=self.instance.pk  # ⚠️ CRUCIAL : On exclut la réservation en cours de modification
                ).exclude(
                    status__in=["rejected", "cancelled"]
                )

                if conflits.exists():
                    self.add_error(
                        "start_date",
                        "Ce panneau est déjà réservé sur tout ou partie de la période sélectionnée."
                    )


        if panel_face:
            if monthly_price in (None, ""):
                cleaned_data["monthly_price"] = panel_face.monthly_price
            else:
                cleaned_data["monthly_price"] = monthly_price

            if duration_months:
                cleaned_data["total_price"] = cleaned_data["monthly_price"] * duration_months

        return cleaned_data

    def save(self, commit=True):
        reservation = super().save(commit=False)

        reservation.end_date = self.cleaned_data["end_date"]
        reservation.monthly_price = self.cleaned_data["monthly_price"]
        reservation.total_price = self.cleaned_data["total_price"]

        if commit:
            reservation.save()

        return reservation