from django.db import models
from django.core.exceptions import ValidationError


class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(
        max_length=2,
        unique=True,
        help_text="Code ISO 3166-1 alpha-2, ex: BF, CI, CM",
    )

    class Meta:
        verbose_name = "Pays"
        verbose_name_plural = "Pays"
        ordering = ["name"]

    def __str__(self):
        return self.name


class GeographicLevel(models.Model):
    country = models.ForeignKey(
        Country, on_delete=models.PROTECT, related_name="levels"
    )
    name = models.CharField(
        max_length=50,
        help_text="Libellé local du niveau, ex: Ville, District, Commune, Quartier",
    )
    order = models.PositiveSmallIntegerField(
        help_text="1 = niveau le plus large (juste sous le pays), "
                   "valeur croissante = niveau le plus fin",
    )

    class Meta:
        verbose_name = "Niveau géographique"
        verbose_name_plural = "Niveaux géographiques"
        ordering = ["country", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["country", "order"], name="unique_order_per_country"
            ),
            models.UniqueConstraint(
                fields=["country", "name"], name="unique_name_per_country"
            ),
        ]

    def __str__(self):
        return f"{self.country.code} — {self.name} (niveau {self.order})"


class GeographicUnit(models.Model):
    country = models.ForeignKey(
        Country, on_delete=models.PROTECT, related_name="units"
    )
    level = models.ForeignKey(
        GeographicLevel, on_delete=models.PROTECT, related_name="units"
    )
    name = models.CharField(max_length=150)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )

    class Meta:
        verbose_name = "Unité géographique"
        verbose_name_plural = "Unités géographiques"
        ordering = ["country", "level__order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["level", "parent", "name"],
                name="unique_unit_per_parent",
            ),
        ]
        indexes = [
            models.Index(fields=["country", "level"]),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.level_id and self.country_id and self.level.country_id != self.country_id:
            raise ValidationError(
                "Le pays de l'unité doit correspondre au pays du niveau choisi."
            )

        if self.parent_id:
            if self.parent.country_id != self.country_id:
                raise ValidationError("Le parent doit appartenir au même pays.")
            if self.parent.level.order != self.level.order - 1:
                raise ValidationError(
                    "Le parent doit être du niveau immédiatement supérieur."
                )
        elif self.level.order != 1:
            raise ValidationError(
                "Seules les unités de niveau 1 peuvent être sans parent."
            )

    def full_path(self):
        parts = [self.name]
        node = self.parent
        while node:
            parts.append(node.name)
            node = node.parent
        return " > ".join(parts)

    def display_path(self):
        """Ex: 'Ouagadougou' pour une ville seule,
        'Ouagadougou - Gounghin' pour un quartier."""
        parts = [self.name]
        node = self.parent
        while node:
            parts.append(node.name)
            node = node.parent
        return " - ".join(reversed(parts))

    def root(self):
        """Retourne l'unité racine (Ville/District), elle-même si déjà racine."""
        node = self
        while node.parent:
            node = node.parent
        return node

    def path_below_root(self):
        """Tout ce qui est sous la racine, ex: 'Koumassi > Soweto'.
        Retourne une chaîne vide si l'unité EST la racine."""
        parts = []
        node = self
        while node.parent:
            parts.append(node.name)
            node = node.parent
        return " > ".join(reversed(parts))

    def get_ancestor_ids(self):
        """Retourne les ID de tous les parents, du plus proche au plus lointain."""
        ids = []
        node = self.parent
        while node:
            ids.append(node.id)
            node = node.parent
        return ids

    def get_descendant_ids(self):
        """Retourne son propre ID + les ID de tous ses descendants (récursif)."""
        ids = [self.id]
        for child in self.children.all():
            ids.extend(child.get_descendant_ids())
        return ids