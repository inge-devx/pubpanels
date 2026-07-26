from django import forms

from apps.panels.models import Panel, PanelFace, PanelFaceImage
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
            "geographic_unit",
            "address",
            "latitude",
            "longitude",
            "description",
            "status",
            "is_published",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "latitude": (
                "Optionnel. Depuis Google Maps, placez un repère sur le panneau et "
                "copiez la latitude."
            ),
            "longitude": (
                "Optionnel. Depuis Google Maps, placez un repère sur le panneau et "
                "copiez la longitude."
            ),
            "geographic_unit": (
                "Sélectionnez l'unité géographique la plus précise disponible "
                "(quartier si connu, sinon ville)."
            ),
            "is_published": (
                "Un panneau inactif ne peut pas rester publié."
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        if self.user and self.user.role != User.Role.SUPER_ADMIN:
            self.fields["agency"].queryset = self.fields["agency"].queryset.filter(
                id=self.user.agency_id
            )
            self.fields["agency"].initial = self.user.agency

        self.fields["title"].label = "Nom du panneau"
        self.fields["reference"].label = "Référence"
        self.fields["format_category"].label = "Catégorie de format"
        self.fields["width_m"].label = "Largeur (m)"
        self.fields["height_m"].label = "Hauteur (m)"
        self.fields["geographic_unit"].label = "Localisation (unité géographique)"
        self.fields["address"].label = "Adresse"
        self.fields["description"].label = "Description"
        self.fields["status"].label = "Statut du panneau"
        self.fields["is_published"].label = "Publier dans le catalogue public"

    def clean(self):
        cleaned_data = super().clean()

        status = cleaned_data.get("status")
        is_published = cleaned_data.get("is_published")

        if status != Panel.Status.ACTIVE and is_published:
            cleaned_data["is_published"] = False

        return cleaned_data

    def save(self, commit=True):
        panel = super().save(commit=False)

        if self.user and self.user.role != User.Role.SUPER_ADMIN:
            panel.agency = self.user.agency

        if panel.status != Panel.Status.ACTIVE:
            panel.is_published = False

        if commit:
            panel.save()

        return panel


class PanelFaceForm(forms.ModelForm):
    class Meta:
        model = PanelFace
        fields = [
            "panel",
            "code",
            "orientation",
            "monthly_price",
            "operational_status",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "orientation": "Exemple : vers centre-ville, axe nord-sud, côté circulation montante.",
            "monthly_price": "Montant mensuel de location pour cette face.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["panel"].widget = forms.HiddenInput()
        self.fields["code"].label = "Code de la face"
        self.fields["orientation"].label = "Orientation"
        self.fields["monthly_price"].label = "Prix mensuel"
        self.fields["operational_status"].label = "Statut opérationnel"
        self.fields["notes"].label = "Notes"


class PanelFaceImageForm(forms.ModelForm):
    class Meta:
        model = PanelFaceImage
        fields = [
            "face",
            "image",
            "caption",
            "is_primary",
            "is_cover_for_panel",
            "display_order",
        ]
        help_texts = {
            "caption": "Texte court décrivant l’image ou l’angle de vue.",
            "is_primary": "Une seule image principale est autorisée par face.",
            "is_cover_for_panel": (
                "Cette image pourra être utilisée plus tard comme image de couverture "
                "du panneau dans le catalogue."
            ),
            "display_order": "Ordre d’affichage dans la galerie de la face.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["face"].widget = forms.HiddenInput()
        self.fields["caption"].label = "Légende"
        self.fields["is_primary"].label = "Image principale"
        self.fields["is_cover_for_panel"].label = "Utiliser comme couverture du panneau"
        self.fields["display_order"].label = "Ordre d’affichage"