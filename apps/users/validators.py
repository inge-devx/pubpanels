import re
from django.core.exceptions import ValidationError

class ComplexityPasswordValidator:
    def validate(self, password, user=None):
        # Vérifie au moins une majuscule
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                "Le mot de passe doit contenir au moins une lettre majuscule.",
                code='password_no_uppercase',
            )
        # Vérifie au moins un chiffre
        if not re.search(r'[0-9]', password):
            raise ValidationError(
                "Le mot de passe doit contenir au moins un chiffre.",
                code='password_no_number',
            )
        # Vérifie au moins un caractère spécial
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]~`\\/;]', password):
            raise ValidationError(
                "Le mot de passe doit contenir au moins un caractère spécial.",
                code='password_no_special',
            )

    def get_help_text(self):
        return "Votre mot de passe doit contenir au moins 10 caractères, inclure une majuscule, un chiffre et un caractère spécial."
