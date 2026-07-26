from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.agencies.models import Agency
from apps.panels.models import Panel, PanelFace
from apps.geography.models import GeographicUnit


PANELS_DATA = [
    # (pays, nom_quartier, adresse, format, largeur, hauteur, lat, lng)
    ("BF", "Belle Ville", "En face de la pharmacie Ayat, premier carré à gauche", "standard", 4, 4, 11.1771, -4.2979),
    ("BF", "Belle Ville", "Carrefour Bounkiougou, sortie sud", "large", 6, 4, 11.1795, -4.2951),
    ("BF", "Accart-Ville", "Avenue de la Nation, près du marché", "standard", 4, 3, 11.1839, -4.2833),
    ("BF", "Sarfalao", "Route de Banfora, station Total", "small", 3, 3, 11.1690, -4.3050),
    ("BF", "Colma", "Entrée université Nazi Boni", "xl", 8, 4, 11.1502, -4.3122),
    ("BF", "Zone du Bois", "Avenue Kwame Nkrumah, face à la clinique", "standard", 4, 4, 12.3686, -1.5197),
    ("BF", "Ouaga 2000", "Rond-point des Nations Unies", "large", 6, 4, 12.3345, -1.5010),
    ("BF", "Gounghin", "Marché de Gounghin, entrée principale", "small", 3, 3, 12.3603, -1.5389),
    ("BF", "Dapoya", "Carrefour Dapoya, sens Ouaga-Kaya", "standard", 4, 4, 12.3822, -1.5145),
    ("BF", "Tanghin", "Route de Kaya, face station Petrofa", "xl", 8, 4, 12.3910, -1.5063),
    ("CI", "Soweto", "En face du camp de la 45ème division", "standard", 4, 4, 5.2893, -3.9862),
    ("CI", "Sicogi", "Carrefour Sicogi, sortie autoroute", "large", 6, 4, 5.2841, -3.9755),
    ("CI", "Angré", "Boulevard Latrille, face pharmacie Angré", "xl", 8, 4, 5.3702, -3.9819),
    ("CI", "Riviera", "Riviera 2, non loin du carrefour Duncan", "standard", 4, 3, 5.3591, -3.9614),
    ("CI", "Selmer", "Marché de Selmer 1, entrée principale", "small", 3, 3, 5.3260, -4.0653),
    ("CI", "Zone 4", "Rue du Canal, face aux entrepôts", "large", 6, 4, 5.2963, -3.9887),
    ("CI", "Arras", "Avenue 16, proche gare routière", "standard", 4, 4, 5.2953, -4.0089),
]

AGENCY_SEED = {
    "BF": {"name": "Régie Faso Pub", "slug": "regie-faso-pub", "email": "contact@fasopub.bf"},
    "CI": {"name": "Régie Ivoire Affichage", "slug": "regie-ivoire-affichage", "email": "contact@ivoireaffichage.ci"},
}

def get_top_level_name(geographic_unit):
    """Remonte jusqu'à l'unité de niveau 1 (Ville/District) pour remplir
    le champ legacy `city`, encore obligatoire pendant la transition."""
    node = geographic_unit
    while node.parent is not None:
        node = node.parent
    return node.name


class Command(BaseCommand):
    help = "Crée des panneaux de démonstration au Burkina Faso et en Côte d'Ivoire"

    @transaction.atomic
    def handle(self, *args, **options):
        agencies = {}
        for code, data in AGENCY_SEED.items():
            agency = Agency.objects.filter(country=code).first()
            if not agency:
                agency = Agency.objects.create(country=code, **data)
                self.stdout.write(f"Régie créée : {agency.name}")
            agencies[code] = agency

        counters = {"BF": 0, "CI": 0}

        for country, quartier_name, address, fmt, width, height, lat, lng in PANELS_DATA:
            counters[country] += 1
            reference = f"{country}-{counters[country]:03d}"
            agency = agencies[country]

            geographic_unit = GeographicUnit.objects.filter(
                country__code=country, name=quartier_name
            ).first()
            if not geographic_unit:
                self.stdout.write(self.style.ERROR(
                    f"Unité géographique introuvable : {quartier_name} ({country}) — panneau ignoré."
                ))
                continue

            panel, created = Panel.objects.get_or_create(
                agency=agency,
                reference=reference,
                defaults=dict(
                    country=country,
                    geographic_unit=geographic_unit,
                    city=get_top_level_name(geographic_unit),
                    district=quartier_name,
                    address=address,
                    latitude=Decimal(str(lat)),
                    longitude=Decimal(str(lng)),
                    format_category=fmt,
                    width_m=Decimal(str(width)),
                    height_m=Decimal(str(height)),
                    status=Panel.Status.ACTIVE,
                    is_published=True,
                ),
            )

            if created:
                PanelFace.objects.get_or_create(
                    panel=panel, code=PanelFace.FaceCode.A,
                    defaults={"monthly_price": Decimal("150000.00")},
                )
                self.stdout.write(f"Panneau créé : {panel.reference} -> {geographic_unit.full_path()}")

        self.stdout.write(self.style.SUCCESS(f"{sum(counters.values())} panneaux traités."))