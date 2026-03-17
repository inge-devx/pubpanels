from datetime import timedelta

from django import forms

from apps.panels.models import PanelFace

from .models import Client, Reservation


class PublicReservationRequestForm(forms.Form):
    company_name = forms.CharField(max_length=150, required=False, label="Entreprise")
    contact_name = forms.CharField(max_length=150, label="Nom du contact")
    phone = forms.CharField(max_length=30, label="Téléphone")
    email = forms.EmailField(required=False, label="Email")
    business_sector = forms.CharField(max_length=100, required=False, label="Secteur d'activité")

    panel_face = forms.ModelChoiceField(
        queryset=PanelFace.objects.none(),
        label="Face du panneau",
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Date de début",
    )
    duration_months = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Nombre de mois",
        help_text="1 mois commercial = 30 jours.",
    )
    need_design_help = forms.BooleanField(required=False, label="Besoin d'aide pour le design")
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea,
        label="Commentaire",
    )

    def __init__(self, *args, panel=None, **kwargs):
        self.panel = panel
        super().__init__(*args, **kwargs)

        queryset = PanelFace.objects.select_related("panel", "panel__agency").filter(
            panel__is_published=True,
            panel__agency__status="active",
            operational_status=PanelFace.OperationalStatus.AVAILABLE,
        )

        if self.panel is not None:
            queryset = queryset.filter(panel=self.panel)

        self.fields["panel_face"].queryset = queryset.order_by("panel__reference", "code")

        if self.panel is not None and queryset.count() == 1:
            self.fields["panel_face"].initial = queryset.first()

    def clean_panel_face(self):
        panel_face = self.cleaned_data["panel_face"]

        if not panel_face.panel.is_published:
            raise forms.ValidationError("This panel is not publicly available.")

        if panel_face.panel.agency.status != "active":
            raise forms.ValidationError("This panel is not available from an active agency.")

        if panel_face.operational_status != PanelFace.OperationalStatus.AVAILABLE:
            raise forms.ValidationError("This face is not currently available.")

        if self.panel is not None and panel_face.panel_id != self.panel.id:
            raise forms.ValidationError("The selected face does not belong to the selected panel.")

        return panel_face

    def build_reservation_dates(self):
        start_date = self.cleaned_data["start_date"]
        duration_months = self.cleaned_data["duration_months"]
        end_date = start_date + timedelta(days=(30 * duration_months) - 1)
        return start_date, end_date

    def get_or_create_client(self):
        company_name = self.cleaned_data["company_name"]
        contact_name = self.cleaned_data["contact_name"]
        phone = self.cleaned_data["phone"]
        email = self.cleaned_data["email"]
        business_sector = self.cleaned_data["business_sector"]

        client = Client.objects.filter(
            contact_name=contact_name,
            phone=phone,
            email=email,
        ).first()

        if client:
            changed = False
            if company_name and client.company_name != company_name:
                client.company_name = company_name
                changed = True
            if business_sector and client.business_sector != business_sector:
                client.business_sector = business_sector
                changed = True
            if changed:
                client.save()
            return client

        return Client.objects.create(
            company_name=company_name,
            contact_name=contact_name,
            phone=phone,
            email=email,
            business_sector=business_sector,
        )

    def save(self):
        client = self.get_or_create_client()
        panel_face = self.cleaned_data["panel_face"]
        start_date, end_date = self.build_reservation_dates()
        duration_months = self.cleaned_data["duration_months"]
        monthly_price = panel_face.monthly_price
        total_price = monthly_price * duration_months

        reservation = Reservation.objects.create(
            agency=panel_face.panel.agency,
            panel_face=panel_face,
            client=client,
            source=Reservation.Source.PLATFORM,
            status=Reservation.Status.PENDING,
            start_date=start_date,
            end_date=end_date,
            monthly_price=monthly_price,
            total_price=total_price,
            need_design_help=self.cleaned_data["need_design_help"],
            notes=self.cleaned_data["notes"],
            created_by=None,
        )
        return reservation