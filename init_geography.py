import os
import django

# Initialisation de l'environnement Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.settings")
django.setup()

from apps.geography.models import Country, GeographicLevel, GeographicUnit


def create_geography_data():
    print("--- Début de l'initialisation géographique réelle ---")

    # ==========================================
    # 1. CRÉATION DES PAYS
    # ==========================================
    bf, _ = Country.objects.get_or_create(name="Burkina Faso", code="BF")
    ci, _ = Country.objects.get_or_create(name="Côte d'Ivoire", code="CI")
    print("✓ Pays configurés.")

    # ==========================================
    # 2. CONFIGURATION DES NIVEAUX LOCAUX
    # ==========================================
    # Burkina Faso : Pays -> Ville (1) -> Quartier (2)
    bf_l1, _ = GeographicLevel.objects.get_or_create(country=bf, name="Ville", order=1)
    bf_l2, _ = GeographicLevel.objects.get_or_create(country=bf, name="Quartier", order=2)

    # Côte d'Ivoire : Pays -> District (1) -> Commune (2) -> Quartier (3)
    ci_l1, _ = GeographicLevel.objects.get_or_create(country=ci, name="District", order=1)
    ci_l2, _ = GeographicLevel.objects.get_or_create(country=ci, name="Commune", order=2)
    ci_l3, _ = GeographicLevel.objects.get_or_create(country=ci, name="Quartier", order=3)
    print("✓ Niveaux administratifs calés sur la réalité.")

    # ==========================================
    # 3. UNITÉS GÉOGRAPHIQUES : BURKINA FASO
    # ==========================================
    # Niveau 1 : Villes (Pas de parent)
    ouaga = GeographicUnit.objects.create(country=bf, level=bf_l1, name="Ouagadougou", parent=None)
    bobo = GeographicUnit.objects.create(country=bf, level=bf_l1, name="Bobo-Dioulasso", parent=None)

    # Niveau 2 : Quartiers de Ouaga (Parent = Ville d'Ouaga)
    GeographicUnit.objects.create(country=bf, level=bf_l2, name="Gounghin", parent=ouaga)
    GeographicUnit.objects.create(country=bf, level=bf_l2, name="Dassasgho", parent=ouaga)
    GeographicUnit.objects.create(country=bf, level=bf_l2, name="Patte d'Oie", parent=ouaga)

    # Niveau 2 : Quartiers de Bobo (Parent = Ville de Bobo)
    GeographicUnit.objects.create(country=bf, level=bf_l2, name="Sarfalao", parent=bobo)
    GeographicUnit.objects.create(country=bf, level=bf_l2, name="Diarradougou", parent=bobo)
    GeographicUnit.objects.create(country=bf, level=bf_l2, name="Accart-ville", parent=bobo)

    # ==========================================
    # 4. UNITÉS GÉOGRAPHIQUES : CÔTE D'IVOIRE
    # ==========================================
    # Niveau 1 : Districts (Pas de parent)
    dist_abidjan = GeographicUnit.objects.create(country=ci, level=ci_l1, name="District Autonome d'Abidjan",
                                                 parent=None)
    dist_yamoussoukro = GeographicUnit.objects.create(country=ci, level=ci_l1, name="District Autonome de Yamoussoukro",
                                                      parent=None)

    # Niveau 2 : Communes d'Abidjan (Parent = District d'Abidjan)
    cocody = GeographicUnit.objects.create(country=ci, level=ci_l2, name="Cocody", parent=dist_abidjan)
    marcory = GeographicUnit.objects.create(country=ci, level=ci_l2, name="Marcory", parent=dist_abidjan)
    yopougon = GeographicUnit.objects.create(country=ci, level=ci_l2, name="Yopougon", parent=dist_abidjan)

    # Niveau 2 : Communes de Yamoussoukro (Parent = District de Yamoussoukro)
    yamoussoukro_commune = GeographicUnit.objects.create(country=ci, level=ci_l2, name="Yamoussoukro Commune",
                                                         parent=dist_yamoussoukro)

    # Niveau 3 : Quartiers des Communes (Parent = Commune obligatoire pour l'ordre 3)
    # Quartiers de Cocody
    GeographicUnit.objects.create(country=ci, level=ci_l3, name="Angré", parent=cocody)
    GeographicUnit.objects.create(country=ci, level=ci_l3, name="Deux Plateaux", parent=cocody)

    # Quartiers de Marcory
    GeographicUnit.objects.create(country=ci, level=ci_l3, name="Zone 4", parent=marcory)
    GeographicUnit.objects.create(country=ci, level=ci_l3, name="Anoumabo", parent=marcory)

    # Quartiers de Yamoussoukro Commune
    GeographicUnit.objects.create(country=ci, level=ci_l3, name="220 Logements", parent=yamoussoukro_commune)
    GeographicUnit.objects.create(country=ci, level=ci_l3, name="Morofe", parent=yamoussoukro_commune)

    print("✓ Unités géographiques réelles insérées avec succès.")
    print("--- Initialisation terminée ---")


if __name__ == "__main__":
    create_geography_data()
