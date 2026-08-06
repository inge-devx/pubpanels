from django import forms
from django.contrib.auth.forms import UserCreationForm
from apps.agencies.models import Agency
from apps.users.models import User


class UserRegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "email", "first_name", "last_name", "role", "agency"]

    def __init__(self, *args, current_user=None, **kwargs):
        self.current_user = current_user
        super().__init__(*args, **kwargs)

        # 🧼 NETTOYAGE DYNAMIQUE : Récupère le texte d'aide de nos nouveaux validateurs de sécurité
        if "password1" in self.fields:
            # Django va compiler automatiquement les règles du settings.py ici
            from django.contrib.auth.password_validation import password_validators_help_text_html
            self.fields[
                "password1"].help_text = "Le mot de passe doit contenir au moins 10 caractères, inclure une majuscule, un chiffre et un caractère spécial."

            self.fields["password1"].widget.attrs.update({
                'style': 'padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; width: 100%; box-sizing: border-box;'
            })

        if "password2" in self.fields:
            self.fields["password2"].help_text = "Saisissez le même mot de passe que précédemment, pour vérification."
            self.fields["password2"].widget.attrs.update({
                'style': 'padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; width: 100%; box-sizing: border-box;'
            })

        # 🔒 PROTECTION 1 : Bridage des rôles selon l'orthographe stricte de votre modèle User
        if self.current_user:
            if self.current_user.role == User.Role.SUPER_ADMIN:
                self.fields["role"].choices = User.Role.choices
            elif self.current_user.role == User.Role.AGENCY_ADMIN:
                # L'admin d'agence ne peut créer que des techniciens/commerciaux (managers)
                self.fields["role"].choices = [
                    (User.Role.AGENCY_MANAGER, "Gestionnaire d'Agence")
                ]
                self.fields["role"].initial = User.Role.AGENCY_MANAGER

                # 🔒 PROTECTION 2 : Forcer l'agence de la régie connectée
                self.fields["agency"].queryset = Agency.objects.filter(id=self.current_user.agency_id)
                self.fields["agency"].initial = self.current_user.agency
                self.fields["agency"].widget = forms.HiddenInput()

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        # 🔒 SÉCURITÉ : On retire "username" pour bloquer la modification de l'identifiant et stabiliser la session
        fields = ["email", "first_name", "last_name", "role", "agency"]

    def __init__(self, *args, current_user=None, **kwargs):
        self.current_user = current_user
        super().__init__(*args, **kwargs)

        # 🎨 Application du style harmonisé sur les champs restants
        for field_name in ["email", "first_name", "last_name", "role", "agency"]:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'style': 'padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; width: 100%; box-sizing: border-box;'
                })

        # 🔒 PROTECTION : Cloisonnement strict des rôles (inchangé)
        if self.current_user:
            if self.current_user.role == User.Role.SUPER_ADMIN:
                self.fields["role"].choices = User.Role.choices
            elif self.current_user.role == User.Role.AGENCY_ADMIN:
                self.fields["role"].choices = [
                    (User.Role.AGENCY_MANAGER, "Gestionnaire d'Agence")
                ]
                self.fields["agency"].queryset = Agency.objects.filter(id=self.current_user.agency_id)
                self.fields["agency"].widget = forms.HiddenInput()

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "first_name", "last_name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Application de votre style propre
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({
                'style': 'padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; width: 100%; box-sizing: border-box;'
            })


