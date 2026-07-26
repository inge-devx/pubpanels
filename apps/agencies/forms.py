from django import forms

from apps.agencies.models import Agency


class AgencyForm(forms.ModelForm):
    class Meta:
        model = Agency
        fields = [
            "name",
            "slug",
            "email",
            "phone",
            "country",
            "geographic_unit",
            "address",
            "status",
            "commission_rate",
            "alert_days_before_expiry",
            "header_image",
            "footer_image",
        ]
        help_texts = {
            "header_image": "Bandeau d'en-tête pour les PDF (PNG/JPG, format large, ex. 1200x200 px).",
            "footer_image": "Bandeau de pied de page pour les PDF (PNG/JPG, format fin, ex. 1200x150 px).",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].label = "Nom de la régie"
        self.fields["slug"].label = "Identifiant (slug)"
        self.fields["email"].label = "Email"
        self.fields["phone"].label = "Téléphone"
        self.fields["country"].label = "Pays"
        self.fields["geographic_unit"].label = "Localisation du siège"
        self.fields["address"].label = "Adresse"
        self.fields["status"].label = "Statut"
        self.fields["commission_rate"].label = "Taux de commission (%)"
        self.fields["alert_days_before_expiry"].label = "Alerte avant expiration (jours)"
        self.fields["header_image"].label = "Bandeau d'en-tête"
        self.fields["footer_image"].label = "Bandeau de pied de page"


class AgencyProfileForm(forms.ModelForm):
    """Formulaire restreint : ce qu'une régie peut modifier elle-même."""

    class Meta:
        model = Agency
        fields = [
            "email",
            "phone",
            "geographic_unit",
            "address",
            "header_image",
            "footer_image",
        ]
        help_texts = {
            "header_image": "Bandeau d'en-tête pour les PDF (PNG/JPG, format large, ex. 1200x200 px).",
            "footer_image": "Bandeau de pied de page pour les PDF (PNG/JPG, format fin, ex. 1200x150 px).",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "Email"
        self.fields["phone"].label = "Téléphone"
        self.fields["geographic_unit"].label = "Localisation du siège"
        self.fields["address"].label = "Adresse"
        self.fields["header_image"].label = "Bandeau d'en-tête"
        self.fields["footer_image"].label = "Bandeau de pied de page"