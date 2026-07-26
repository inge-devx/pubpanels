from django.core.management.base import BaseCommand
from django.db import transaction
from apps.geography.models import Country, GeographicLevel, GeographicUnit
from apps.core.constants import COUNTRY_CHOICES


class Command(BaseCommand):
    help = "Crée les pays, niveaux et unités géographiques de base"

    @transaction.atomic
    def handle(self, *args, **options):
        countries = {}
        for code, name in COUNTRY_CHOICES:
            country, _ = Country.objects.get_or_create(code=code, defaults={"name": name})
            countries[code] = country

        # ---------------- BURKINA FASO ----------------
        bf = countries["BF"]
        lvl_ville_bf, _ = GeographicLevel.objects.get_or_create(country=bf, name="Ville", order=1)
        lvl_quartier_bf, _ = GeographicLevel.objects.get_or_create(country=bf, name="Quartier", order=2)

        bf_data = {
            "Bobo-Dioulasso": ["Belle Ville", "Accart-Ville", "Sarfalao", "Colma", "Diarradougou"],
            "Ouagadougou": ["Zone du Bois", "Ouaga 2000", "Gounghin", "Dapoya", "Tanghin"],
        }
        for city_name, quartiers in bf_data.items():
            city_unit, _ = GeographicUnit.objects.get_or_create(
                country=bf, level=lvl_ville_bf, name=city_name, parent=None
            )
            for q in quartiers:
                GeographicUnit.objects.get_or_create(
                    country=bf, level=lvl_quartier_bf, name=q, parent=city_unit
                )

        # ---------------- COTE D'IVOIRE ----------------
        ci = countries["CI"]
        lvl_district, _ = GeographicLevel.objects.get_or_create(country=ci, name="District", order=1)
        lvl_commune, _ = GeographicLevel.objects.get_or_create(country=ci, name="Commune", order=2)
        lvl_quartier_ci, _ = GeographicLevel.objects.get_or_create(country=ci, name="Quartier", order=3)

        abidjan, _ = GeographicUnit.objects.get_or_create(
            country=ci, level=lvl_district, name="Abidjan", parent=None
        )

        ci_data = {
            "Koumassi": ["Soweto", "Sicogi", "Remblais"],
            "Cocody": ["Angré", "Riviera", "Danga"],
            "Yopougon": ["Selmer", "Niangon", "Wassakara"],
            "Marcory": ["Zone 4", "Anoumabo"],
            "Treichville": ["Arras", "Belleville"],
        }
        for commune_name, quartiers in ci_data.items():
            commune_unit, _ = GeographicUnit.objects.get_or_create(
                country=ci, level=lvl_commune, name=commune_name, parent=abidjan
            )
            for q in quartiers:
                GeographicUnit.objects.get_or_create(
                    country=ci, level=lvl_quartier_ci, name=q, parent=commune_unit
                )

        # ---------------- AUTRES PAYS (squelette) ----------------
        for code in ["ML", "NE", "GH", "TG", "BJ", "SN"]:
            country = countries[code]
            GeographicLevel.objects.get_or_create(country=country, name="Ville", order=1)
            GeographicLevel.objects.get_or_create(country=country, name="Quartier", order=2)

        self.stdout.write(self.style.SUCCESS("Seeding géographique terminé."))