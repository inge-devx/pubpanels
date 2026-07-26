from django import forms

from apps.reservations.models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            "company_name",
            "contact_name",
            "phone",
            "email",
            "business_sector",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        super().__init__(*args, **kwargs)

        if self.user and self.user.role != self.user.Role.SUPER_ADMIN:
            self.fields.pop("agency", None)

        self.fields["company_name"].label = "Entreprise"
        self.fields["contact_name"].label = "Nom du contact"
        self.fields["phone"].label = "Téléphone"
        self.fields["email"].label = "Email"
        self.fields["business_sector"].label = "Secteur d’activité"