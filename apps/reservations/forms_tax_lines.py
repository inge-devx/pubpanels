from django import forms

from apps.reservations.models import ReservationTaxLine


class ReservationTaxLineForm(forms.ModelForm):
    class Meta:
        model = ReservationTaxLine
        fields = ["label", "line_type", "computation_mode", "rate_percent", "fixed_amount", "order"]
        widgets = {
            "order": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["label"].label = "Libellé"
        self.fields["label"].widget.attrs["placeholder"] = "Ex : TVA, Retenue à la source..."
        self.fields["line_type"].label = "Type"
        self.fields["computation_mode"].label = "Mode de calcul"
        self.fields["rate_percent"].label = "Taux (%)"
        self.fields["fixed_amount"].label = "Montant fixe (FCFA)"
        self.fields["rate_percent"].required = False
        self.fields["fixed_amount"].required = False
        self.fields["order"].initial = 0