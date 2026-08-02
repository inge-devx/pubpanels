import os
import sys

# ==============================================================================
# 1. CONFIGURATION BRUTE WINDOWS / GDAL (AVANT LES IMPORTS GÉOSPATIAUX DJANGO)
# ==============================================================================
if os.name == 'nt':
    OSGEO4W_ROOT = r"C:\OSGeo4W"
    os.environ['PATH'] = os.path.join(OSGEO4W_ROOT, 'bin') + os.path.pathsep + os.environ['PATH']
    os.environ['GDAL_LIBRARY_PATH'] = os.path.join(OSGEO4W_ROOT, 'bin', 'gdal309.dll')
    os.environ['PROJ_LIB'] = os.path.join(OSGEO4W_ROOT, 'share', 'proj')

# Initialisation obligatoire de Django
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.settings")
django.setup()

# ==============================================================================
# 2. LES IMPORTS GÉOGRAPHIQUES ET MODÈLES (TOUJOURS APRÈS DJANGO.SETUP())
# ==============================================================================
from django.contrib.gis.geos import Point
from apps.agencies.models import Agency
from apps.geography.models import GeographicUnit
from apps.panels.models import Panel, PanelFace  # Modifiez PanelFace par Face si nécessaire


def create_panels_data():
    print("--- Début de l'initialisation des Régies et Panneaux ---")

    # ==========================================
    # 3. RÉCUPÉRATION DES UNITÉS GÉOGRAPHIQUES
    # ==========================================
    try:
        # Burkina Faso
        gounghin = GeographicUnit.objects.get(name="Gounghin")
        patte_oie = GeographicUnit.objects.get(name="Patte d'Oie")
        sarfalao = GeographicUnit.objects.get(name="Sarfalao")
        ouaga_ville = GeographicUnit.objects.get(name="Ouagadougou")

        # Côte d'Ivoire
        angre = GeographicUnit.objects.get(name="Angré")
        zone_4 = GeographicUnit.objects.get(name="Zone 4")
        abidjan_district = GeographicUnit.objects.get(name="District Autonome d'Abidjan")
    except GeographicUnit.DoesNotExist:
        print("❌ Erreur : Les unités géographiques n'existent pas. Lancez d'abord init_geography.py")
        return

    # ==========================================
    # 4. CRÉATION DES RÉGIES (Agencies)
    # ==========================================
    # Régie 1 : Burkina Faso
    regie_faso, _ = Agency.objects.get_or_create(
        name="Faso Affichage Pro",
        defaults={
            "slug": "faso-affichage-pro",
            "geographic_unit": ouaga_ville,
            "country": "BF",  # Code ISO 2 lettres
        }
    )

    # Régie 2 : Côte d'Ivoire
    regie_ebene, _ = Agency.objects.get_or_create(
        name="Ébène Média Ivoir",
        defaults={
            "slug": "ebene-media-ivoir",
            "geographic_unit": abidjan_district,
            "country": "CI",  # Code ISO 2 lettres
        }
    )
    print("✓ Régies créées avec leurs contraintes validées.")

    # ==========================================
    # 5. CRÉATION DES PANNEAUX : BURKINA FASO
    # ==========================================
    # Panneau 1 : Ouaga - Gounghin
    p1, _ = Panel.objects.get_or_create(
        reference="BF-OUA-GOU-001",
        defaults={
            "title": "Panneau Gounghin - Carrefour de la Jeunesse",
            "agency": regie_faso,
            "geographic_unit": gounghin,
            "location": Point(-1.5458, 12.3582),  # Longitude, Latitude
            "address": "Avenue Passore, face à la station",
            "status": "active"
        }
    )
    PanelFace.objects.get_or_create(panel=p1, code="A", defaults={"orientation": "Nord", "monthly_price": 150000,
                                                                  "operational_status": "available"})
    PanelFace.objects.get_or_create(panel=p1, code="B", defaults={"orientation": "Sud", "monthly_price": 150000,
                                                                  "operational_status": "available"})

    # Panneau 2 : Ouaga - Patte d'Oie
    p2, _ = Panel.objects.get_or_create(
        reference="BF-OUA-PDO-002",
        defaults={
            "title": "Panneau Patte d'Oie - Échangeur Sud",
            "agency": regie_faso,
            "geographic_unit": patte_oie,
            "location": Point(-1.5204, 12.3168),
            "address": "Boulevard Mouammar Kadhafi",
            "status": "active"
        }
    )
    PanelFace.objects.get_or_create(panel=p2, code="A", defaults={"orientation": "Est", "monthly_price": 200000,
                                                                  "operational_status": "available"})

    # Panneau 3 : Bobo - Sarfalao
    p3, _ = Panel.objects.get_or_create(
        reference="BF-BOB-SAR-003",
        defaults={
            "title": "Panneau Sarfalao - Axe Principal",
            "agency": regie_faso,
            "geographic_unit": sarfalao,
            "location": Point(-4.2751, 11.1604),
            "address": "Avenue de Châlons, non loin du marché",
            "status": "active"
        }
    )
    PanelFace.objects.get_or_create(panel=p3, code="A", defaults={"orientation": "Ouest", "monthly_price": 120000,
                                                                  "operational_status": "available"})

    # ==========================================
    # 6. CRÉATION DES PANNEAUX : CÔTE D'IVOIRE
    # ==========================================
    # Panneau 4 : Abidjan - Zone 4 (Boulevard VGE)
    p4, _ = Panel.objects.get_or_create(
        reference="CI-ABJ-Z4-001",
        defaults={
            "title": "Panneau Géant Marcory VGE",
            "agency": regie_ebene,
            "geographic_unit": zone_4,
            "location": Point(-3.9925, 5.3082),
            "address": "Boulevard Valéry Giscard d'Estaing, Sortie Pont HKB",
            "status": "active"
        }
    )
    PanelFace.objects.get_or_create(panel=p4, code="A", defaults={"orientation": "Sud-Nord", "monthly_price": 450000,
                                                                  "operational_status": "available"})
    PanelFace.objects.get_or_create(panel=p4, code="B", defaults={"orientation": "Nord-Sud", "monthly_price": 450000,
                                                                  "operational_status": "available"})

    # Panneau 5 : Abidjan - Angré (Boulevard Latrille)
    p5, _ = Panel.objects.get_or_create(
        reference="CI-ABJ-ANG-002",
        defaults={
            "title": "Panneau Angré - Carrefour 22ème Arrondissement",
            "agency": regie_ebene,
            "geographic_unit": angre,
            "location": Point(-3.9784, 5.3991),
            "address": "Boulevard Latrille, proche pharmacie des Berges",
            "status": "active"
        }
    )
    PanelFace.objects.get_or_create(panel=p5, code="A", defaults={"orientation": "Est", "monthly_price": 300000,
                                                                  "operational_status": "available"})

    print("✓ Panneaux et faces publicitaires insérés avec succès.")
    print("--- Initialisation terminée ---")


if __name__ == "__main__":
    create_panels_data()
