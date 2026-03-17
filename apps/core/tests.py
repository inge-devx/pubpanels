from datetime import date
from decimal import Decimal

from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.agencies.models import Agency
from apps.locations.models import City
from apps.panels.models import Panel, PanelFace
from apps.reservations.models import Client, Reservation
from apps.users.models import User


class LocationAndCountryTests(TestCase):
    def setUp(self):
        self.ouaga = City.objects.create(
            country_code="BF",
            name="Ouagadougou",
            slug="ouagadougou",
        )
        self.abidjan = City.objects.create(
            country_code="CI",
            name="Abidjan",
            slug="abidjan",
        )

    def test_agency_country_and_city_ref_must_match(self):
        agency = Agency(
            name="Agence Test",
            slug="agence-test",
            country="BF",
            city_ref=self.abidjan,
        )

        with self.assertRaises(ValidationError):
            agency.full_clean()

    def test_panel_country_and_city_ref_must_match(self):
        agency = Agency.objects.create(
            name="Agence Panel",
            slug="agence-panel",
            country="BF",
            city_ref=self.ouaga,
        )

        panel = Panel(
            agency=agency,
            reference="PANEL-TEST",
            format_category=Panel.FormatCategory.STANDARD,
            width_m=Decimal("4.00"),
            height_m=Decimal("3.00"),
            country="BF",
            city="Abidjan",
            city_ref=self.abidjan,
        )

        with self.assertRaises(ValidationError):
            panel.full_clean()


class PanelFormatCategoryValidationTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(
            country_code="BF",
            name="Ouagadougou",
            slug="ouagadougou",
        )
        self.agency = Agency.objects.create(
            name="Agence Format",
            slug="agence-format",
            country="BF",
            city_ref=self.city,
        )

    def test_small_category_rejects_area_greater_or_equal_12(self):
        panel = Panel(
            agency=self.agency,
            reference="FMT-001",
            format_category=Panel.FormatCategory.SMALL,
            width_m=Decimal("4.00"),
            height_m=Decimal("3.00"),  # 12 m²
            country="BF",
            city="Ouagadougou",
            city_ref=self.city,
        )

        with self.assertRaises(ValidationError):
            panel.full_clean()

    def test_standard_category_accepts_area_between_12_and_less_than_24(self):
        panel = Panel(
            agency=self.agency,
            reference="FMT-002",
            format_category=Panel.FormatCategory.STANDARD,
            width_m=Decimal("4.00"),
            height_m=Decimal("3.00"),  # 12 m²
            country="BF",
            city="Ouagadougou",
            city_ref=self.city,
        )

        panel.full_clean()

    def test_large_category_requires_exactly_24(self):
        panel = Panel(
            agency=self.agency,
            reference="FMT-003",
            format_category=Panel.FormatCategory.LARGE,
            width_m=Decimal("6.00"),
            height_m=Decimal("4.00"),  # 24 m²
            country="BF",
            city="Ouagadougou",
            city_ref=self.city,
        )

        panel.full_clean()

    def test_large_category_rejects_non_24_area(self):
        panel = Panel(
            agency=self.agency,
            reference="FMT-004",
            format_category=Panel.FormatCategory.LARGE,
            width_m=Decimal("4.00"),
            height_m=Decimal("3.00"),  # 12 m²
            country="BF",
            city="Ouagadougou",
            city_ref=self.city,
        )

        with self.assertRaises(ValidationError):
            panel.full_clean()

    def test_xl_category_rejects_area_less_or_equal_24(self):
        panel = Panel(
            agency=self.agency,
            reference="FMT-005",
            format_category=Panel.FormatCategory.XL,
            width_m=Decimal("6.00"),
            height_m=Decimal("4.00"),  # 24 m²
            country="BF",
            city="Ouagadougou",
            city_ref=self.city,
        )

        with self.assertRaises(ValidationError):
            panel.full_clean()

class PublicCatalogTests(TestCase):
    def setUp(self):
        self.ouaga = City.objects.create(
            country_code="BF",
            name="Ouagadougou",
            slug="ouagadougou",
        )
        self.bobo = City.objects.create(
            country_code="BF",
            name="Bobo-Dioulasso",
            slug="bobo-dioulasso",
        )
        self.abidjan = City.objects.create(
            country_code="CI",
            name="Abidjan",
            slug="abidjan",
        )

        self.active_agency = Agency.objects.create(
            name="Agence Active",
            slug="agence-active",
            status=Agency.Status.ACTIVE,
            country="BF",
            city_ref=self.ouaga,
        )
        self.inactive_agency = Agency.objects.create(
            name="Agence Inactive",
            slug="agence-inactive",
            status=Agency.Status.INACTIVE,
            country="CI",
            city_ref=self.abidjan,
        )

        self.public_panel = Panel.objects.create(
            agency=self.active_agency,
            reference="PUBLIC-001",
            format_category=Panel.FormatCategory.LARGE,
            width_m=Decimal("6.00"),
            height_m=Decimal("4.00"),
            country="BF",
            city="Ouagadougou",
            city_ref=self.ouaga,
            is_published=True,
        )
        self.hidden_panel = Panel.objects.create(
            agency=self.active_agency,
            reference="HIDDEN-001",
            format_category=Panel.FormatCategory.STANDARD,
            width_m=Decimal("4.00"),
            height_m=Decimal("3.00"),
            country="BF",
            city="Bobo-Dioulasso",
            city_ref=self.bobo,
            is_published=False,
        )
        self.inactive_agency_panel = Panel.objects.create(
            agency=self.inactive_agency,
            reference="INACTIVE-001",
            format_category=Panel.FormatCategory.XL,
            width_m=Decimal("8.00"),
            height_m=Decimal("4.00"),
            country="CI",
            city="Abidjan",
            city_ref=self.abidjan,
            is_published=True,
        )

        PanelFace.objects.create(
            panel=self.public_panel,
            code=PanelFace.FaceCode.A,
            monthly_price=Decimal("100000.00"),
        )
        PanelFace.objects.create(
            panel=self.public_panel,
            code=PanelFace.FaceCode.B,
            monthly_price=Decimal("120000.00"),
        )

    def test_public_catalog_shows_only_published_panels_from_active_agencies(self):
        response = self.client.get(reverse("public_catalog"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PUBLIC-001")
        self.assertNotContains(response, "HIDDEN-001")
        self.assertNotContains(response, "INACTIVE-001")

    def test_public_catalog_can_filter_by_country(self):
        response = self.client.get(reverse("public_catalog"), {"country": "BF"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PUBLIC-001")

    def test_public_catalog_can_filter_by_city(self):
        response = self.client.get(reverse("public_catalog"), {"country": "BF", "city": self.ouaga.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PUBLIC-001")

    def test_public_catalog_can_filter_by_agency(self):
        response = self.client.get(reverse("public_catalog"), {"agency": self.active_agency.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PUBLIC-001")

    def test_public_catalog_can_filter_by_format_category(self):
        response = self.client.get(
            reverse("public_catalog"),
            {"format_category": Panel.FormatCategory.LARGE},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PUBLIC-001")

    def test_public_panel_detail_shows_only_public_panel(self):
        response = self.client.get(reverse("public_panel_detail", args=[self.public_panel.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PUBLIC-001")
        self.assertContains(response, "Agence Active")
        self.assertContains(response, "Ouagadougou")
        self.assertContains(response, "6.00 m x 4.00 m")

    def test_public_panel_detail_returns_404_for_hidden_panel(self):
        response = self.client.get(reverse("public_panel_detail", args=[self.hidden_panel.id]))

        self.assertEqual(response.status_code, 404)


class PublicReservationRequestTests(TestCase):
    def setUp(self):
        self.ouaga = City.objects.create(
            country_code="BF",
            name="Ouagadougou",
            slug="ouagadougou",
        )

        self.agency = Agency.objects.create(
            name="Agence Publique",
            slug="agence-publique",
            status=Agency.Status.ACTIVE,
            country="BF",
            city_ref=self.ouaga,
        )

        self.panel = Panel.objects.create(
            agency=self.agency,
            reference="PUBLIC-RES-001",
            format_category=Panel.FormatCategory.LARGE,
            width_m=Decimal("6.00"),
            height_m=Decimal("4.00"),
            country="BF",
            city="Ouagadougou",
            city_ref=self.ouaga,
            is_published=True,
        )

        self.face_a = PanelFace.objects.create(
            panel=self.panel,
            code=PanelFace.FaceCode.A,
            monthly_price=Decimal("150000.00"),
            operational_status=PanelFace.OperationalStatus.AVAILABLE,
        )
        self.face_b = PanelFace.objects.create(
            panel=self.panel,
            code=PanelFace.FaceCode.B,
            monthly_price=Decimal("160000.00"),
            operational_status=PanelFace.OperationalStatus.AVAILABLE,
        )

    def test_public_request_page_for_panel_loads(self):
        response = self.client.get(
            reverse("public_reservation_request_for_panel", args=[self.panel.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PUBLIC-RES-001")
        self.assertContains(response, "Agence Publique")

    def test_public_request_creates_client_and_pending_reservation(self):
        response = self.client.post(
            reverse("public_reservation_request_for_panel", args=[self.panel.id]),
            {
                "company_name": "Entreprise X",
                "contact_name": "Jean Client",
                "phone": "70000001",
                "email": "clientx@test.com",
                "business_sector": "Commerce",
                "panel_face": self.face_a.id,
                "start_date": "2026-10-01",
                "duration_months": "2",
                "need_design_help": "on",
                "notes": "Je souhaite réserver rapidement.",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("public_reservation_success"))

        client = Client.objects.get(phone="70000001")
        reservation = Reservation.objects.get(client=client)

        self.assertEqual(client.company_name, "Entreprise X")
        self.assertEqual(reservation.agency, self.agency)
        self.assertEqual(reservation.panel_face, self.face_a)
        self.assertEqual(reservation.source, Reservation.Source.PLATFORM)
        self.assertEqual(reservation.status, Reservation.Status.PENDING)
        self.assertEqual(reservation.monthly_price, Decimal("150000.00"))
        self.assertEqual(reservation.total_price, Decimal("300000.00"))
        self.assertEqual(reservation.created_by, None)
        self.assertEqual(reservation.end_date.isoformat(), "2026-11-29")

    def test_public_request_reuses_existing_client(self):
        existing_client = Client.objects.create(
            company_name="Entreprise X",
            contact_name="Jean Client",
            phone="70000001",
            email="clientx@test.com",
        )

        self.client.post(
            reverse("public_reservation_request_for_panel", args=[self.panel.id]),
            {
                "company_name": "Entreprise X",
                "contact_name": "Jean Client",
                "phone": "70000001",
                "email": "clientx@test.com",
                "business_sector": "Commerce",
                "panel_face": self.face_b.id,
                "start_date": "2026-11-01",
                "duration_months": "1",
                "notes": "Nouvelle demande.",
            },
        )

        self.assertEqual(Client.objects.filter(phone="70000001").count(), 1)
        reservation = Reservation.objects.get(client=existing_client)
        self.assertEqual(reservation.panel_face, self.face_b)

    def test_public_request_rejects_face_from_another_panel_when_panel_is_fixed(self):
        other_panel = Panel.objects.create(
            agency=self.agency,
            reference="PUBLIC-RES-002",
            format_category=Panel.FormatCategory.STANDARD,
            width_m=Decimal("4.00"),
            height_m=Decimal("3.00"),
            country="BF",
            city="Ouagadougou",
            city_ref=self.ouaga,
            is_published=True,
        )
        other_face = PanelFace.objects.create(
            panel=other_panel,
            code=PanelFace.FaceCode.A,
            monthly_price=Decimal("120000.00"),
            operational_status=PanelFace.OperationalStatus.AVAILABLE,
        )

        response = self.client.post(
            reverse("public_reservation_request_for_panel", args=[self.panel.id]),
            {
                "company_name": "Entreprise X",
                "contact_name": "Jean Client",
                "phone": "70000001",
                "email": "clientx@test.com",
                "panel_face": other_face.id,
                "start_date": "2026-10-01",
                "duration_months": "1",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ce choix ne fait pas partie de ceux disponibles")


class PanelCreateViewTests(TestCase):
    def setUp(self):
        self.ouaga = City.objects.create(
            country_code="BF",
            name="Ouagadougou",
            slug="ouagadougou",
        )
        self.bobo = City.objects.create(
            country_code="BF",
            name="Bobo-Dioulasso",
            slug="bobo-dioulasso",
        )
        self.abidjan = City.objects.create(
            country_code="CI",
            name="Abidjan",
            slug="abidjan",
        )

        self.agency_a = Agency.objects.create(
            name="Agence A",
            slug="agence-a",
            email="a@test.com",
            country="BF",
            city_ref=self.ouaga,
        )
        self.agency_b = Agency.objects.create(
            name="Agence B",
            slug="agence-b",
            email="b@test.com",
            country="CI",
            city_ref=self.abidjan,
        )
        self.super_admin = User.objects.create_user(
            username="superadmin",
            password="testpass123",
            role=User.Role.SUPER_ADMIN,
            agency=self.agency_a,
        )
        self.manager = User.objects.create_user(
            username="manager",
            password="testpass123",
            role=User.Role.AGENCY_MANAGER,
            agency=self.agency_a,
        )

    def test_super_admin_can_choose_agency(self):
        self.client.login(username="superadmin", password="testpass123")

        response = self.client.post(
            reverse("panel_create"),
            {
                "agency": self.agency_b.id,
                "reference": "PNL-SUP-001",
                "title": "Panneau super admin",
                "format_category": Panel.FormatCategory.LARGE,
                "width_m": "6.00",
                "height_m": "4.00",
                "country": "CI",
                "city_ref": self.abidjan.id,
                "district": "Centre",
                "address": "Avenue 1",
                "latitude": "12.345678",
                "longitude": "-1.234567",
                "description": "Description",
                "status": Panel.Status.ACTIVE,
                "is_published": "on",
            },
        )

        panel = Panel.objects.get(reference="PNL-SUP-001")
        self.assertRedirects(response, reverse("panel_detail", args=[panel.id]))
        self.assertEqual(panel.agency, self.agency_b)
        self.assertEqual(panel.country, "CI")
        self.assertEqual(panel.city_ref, self.abidjan)
        self.assertEqual(panel.city, "Abidjan")

    def test_non_super_admin_is_forced_to_own_agency(self):
        self.client.login(username="manager", password="testpass123")

        response = self.client.post(
            reverse("panel_create"),
            {
                "agency": self.agency_b.id,
                "reference": "PNL-MNG-001",
                "title": "Panneau manager",
                "format_category": Panel.FormatCategory.STANDARD,
                "width_m": "4.00",
                "height_m": "3.00",
                "country": "BF",
                "city_ref": self.bobo.id,
                "district": "Sud",
                "address": "Rue 2",
                "latitude": "11.111111",
                "longitude": "-2.222222",
                "description": "Description",
                "status": Panel.Status.ACTIVE,
                "is_published": "on",
            },
        )

        panel = Panel.objects.get(reference="PNL-MNG-001")
        self.assertRedirects(response, reverse("panel_detail", args=[panel.id]))
        self.assertEqual(panel.agency, self.agency_a)

    def test_non_super_admin_form_shows_only_own_agency(self):
        self.client.login(username="manager", password="testpass123")

        response = self.client.get(reverse("panel_create"))

        self.assertEqual(response.status_code, 200)
        agency_queryset = response.context["form"].fields["agency"].queryset
        self.assertEqual(list(agency_queryset), [self.agency_a])

    def test_success_message_is_added_after_creation(self):
        self.client.login(username="manager", password="testpass123")

        response = self.client.post(
            reverse("panel_create"),
            {
                "agency": self.agency_a.id,
                "reference": "PNL-MSG-001",
                "title": "Message",
                "format_category": Panel.FormatCategory.STANDARD,
                "width_m": "4.00",
                "height_m": "3.00",
                "country": "BF",
                "city_ref": self.ouaga.id,
                "status": Panel.Status.ACTIVE,
                "is_published": "on",
            },
            follow=True,
        )

        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Panneau créé avec succès.", messages)

    def test_cities_api_filters_by_country(self):
        self.client.login(username="superadmin", password="testpass123")

        response = self.client.get(reverse("cities_by_country_api"), {"country": "BF"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        returned_names = [item["name"] for item in payload["cities"]]
        self.assertIn("Ouagadougou", returned_names)
        self.assertIn("Bobo-Dioulasso", returned_names)
        self.assertNotIn("Abidjan", returned_names)


class PanelDetailAndUpdateViewTests(TestCase):
    def setUp(self):
        self.ouaga = City.objects.create(
            country_code="BF",
            name="Ouagadougou",
            slug="ouagadougou",
        )
        self.bobo = City.objects.create(
            country_code="BF",
            name="Bobo-Dioulasso",
            slug="bobo-dioulasso",
        )
        self.abidjan = City.objects.create(
            country_code="CI",
            name="Abidjan",
            slug="abidjan",
        )

        self.agency_a = Agency.objects.create(
            name="Agence A",
            slug="agence-a",
            email="a@test.com",
            country="BF",
            city_ref=self.ouaga,
        )
        self.agency_b = Agency.objects.create(
            name="Agence B",
            slug="agence-b",
            email="b@test.com",
            country="CI",
            city_ref=self.abidjan,
        )

        self.super_admin = User.objects.create_user(
            username="superadminx",
            password="testpass123",
            role=User.Role.SUPER_ADMIN,
            agency=self.agency_a,
        )
        self.manager_a = User.objects.create_user(
            username="managera",
            password="testpass123",
            role=User.Role.AGENCY_MANAGER,
            agency=self.agency_a,
        )
        self.manager_b = User.objects.create_user(
            username="managerb",
            password="testpass123",
            role=User.Role.AGENCY_MANAGER,
            agency=self.agency_b,
        )

        self.panel_a = Panel.objects.create(
            agency=self.agency_a,
            reference="PANEL-A",
            title="Panneau A",
            format_category=Panel.FormatCategory.STANDARD,
            width_m=Decimal("4.00"),
            height_m=Decimal("3.00"),
            country="BF",
            city="Ouagadougou",
            city_ref=self.ouaga,
            district="Centre",
            status=Panel.Status.ACTIVE,
            is_published=True,
        )

        self.face_a1 = PanelFace.objects.create(
            panel=self.panel_a,
            code=PanelFace.FaceCode.A,
            monthly_price=Decimal("100000.00"),
        )

    def test_super_admin_can_view_panel_detail(self):
        self.client.login(username="superadminx", password="testpass123")

        response = self.client.get(reverse("panel_detail", args=[self.panel_a.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PANEL-A")
        self.assertContains(response, "Panneau A")
        self.assertContains(response, "Ouagadougou")

    def test_agency_user_can_view_own_panel_detail(self):
        self.client.login(username="managera", password="testpass123")

        response = self.client.get(reverse("panel_detail", args=[self.panel_a.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PANEL-A")

    def test_agency_user_cannot_view_other_agency_panel_detail(self):
        self.client.login(username="managerb", password="testpass123")

        response = self.client.get(reverse("panel_detail", args=[self.panel_a.id]))

        self.assertEqual(response.status_code, 404)

    def test_super_admin_can_update_panel(self):
        self.client.login(username="superadminx", password="testpass123")

        response = self.client.post(
            reverse("panel_update", args=[self.panel_a.id]),
            {
                "agency": self.agency_b.id,
                "reference": "PANEL-A-UPDATED",
                "title": "Panneau modifié",
                "format_category": Panel.FormatCategory.XL,
                "width_m": "8.00",
                "height_m": "4.00",
                "country": "CI",
                "city_ref": self.abidjan.id,
                "district": "Sud",
                "address": "Nouvelle adresse",
                "latitude": "11.500000",
                "longitude": "-4.200000",
                "description": "Description modifiée",
                "status": Panel.Status.MAINTENANCE,
                "is_published": "on",
            },
        )

        self.panel_a.refresh_from_db()
        self.assertRedirects(response, reverse("panel_detail", args=[self.panel_a.id]))
        self.assertEqual(self.panel_a.agency, self.agency_b)
        self.assertEqual(self.panel_a.reference, "PANEL-A-UPDATED")
        self.assertEqual(self.panel_a.city_ref, self.abidjan)
        self.assertEqual(self.panel_a.city, "Abidjan")

    def test_agency_user_is_forced_to_keep_own_agency_on_update(self):
        self.client.login(username="managera", password="testpass123")

        response = self.client.post(
            reverse("panel_update", args=[self.panel_a.id]),
            {
                "agency": self.agency_b.id,
                "reference": "PANEL-A-UPDATED-2",
                "title": "Panneau agence",
                "format_category": Panel.FormatCategory.STANDARD,
                "width_m": "4.00",
                "height_m": "3.00",
                "country": "BF",
                "city_ref": self.bobo.id,
                "district": "Centre",
                "address": "Adresse agence",
                "latitude": "12.350000",
                "longitude": "-1.520000",
                "description": "Description agence",
                "status": Panel.Status.ACTIVE,
                "is_published": "on",
            },
        )

        self.panel_a.refresh_from_db()
        self.assertRedirects(response, reverse("panel_detail", args=[self.panel_a.id]))
        self.assertEqual(self.panel_a.agency, self.agency_a)
        self.assertEqual(self.panel_a.city_ref, self.bobo)
        self.assertEqual(self.panel_a.city, "Bobo-Dioulasso")

    def test_agency_user_cannot_update_other_agency_panel(self):
        self.client.login(username="managerb", password="testpass123")

        response = self.client.get(reverse("panel_update", args=[self.panel_a.id]))

        self.assertEqual(response.status_code, 404)

    def test_success_message_is_added_after_update(self):
        self.client.login(username="managera", password="testpass123")

        response = self.client.post(
            reverse("panel_update", args=[self.panel_a.id]),
            {
                "agency": self.agency_a.id,
                "reference": "PANEL-A-MSG",
                "title": "Message update",
                "format_category": Panel.FormatCategory.STANDARD,
                "width_m": "4.00",
                "height_m": "3.00",
                "country": "BF",
                "city_ref": self.ouaga.id,
                "district": "Centre",
                "status": Panel.Status.ACTIVE,
                "is_published": "on",
            },
            follow=True,
        )

        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Panneau mis à jour avec succès.", messages)


class PanelFaceModelTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(
            country_code="BF",
            name="Ouagadougou",
            slug="ouagadougou",
        )
        self.agency = Agency.objects.create(
            name="Agence Test",
            slug="agence-test",
            email="agence@test.com",
            country="BF",
            city_ref=self.city,
        )
        self.panel = Panel.objects.create(
            agency=self.agency,
            reference="PANEL-FACES",
            format_category=Panel.FormatCategory.STANDARD,
            width_m=Decimal("4.00"),
            height_m=Decimal("3.00"),
            country="BF",
            city="Ouagadougou",
            city_ref=self.city,
        )

    def test_can_create_face_codes_up_to_d(self):
        face_a = PanelFace.objects.create(
            panel=self.panel,
            code=PanelFace.FaceCode.A,
            monthly_price=Decimal("100000.00"),
        )
        face_b = PanelFace.objects.create(
            panel=self.panel,
            code=PanelFace.FaceCode.B,
            monthly_price=Decimal("100000.00"),
        )
        face_c = PanelFace.objects.create(
            panel=self.panel,
            code=PanelFace.FaceCode.C,
            monthly_price=Decimal("100000.00"),
        )
        face_d = PanelFace.objects.create(
            panel=self.panel,
            code=PanelFace.FaceCode.D,
            monthly_price=Decimal("100000.00"),
        )

        self.assertEqual(face_a.code, "A")
        self.assertEqual(face_b.code, "B")
        self.assertEqual(face_c.code, "C")
        self.assertEqual(face_d.code, "D")
        self.assertEqual(self.panel.faces.count(), 4)

    def test_cannot_create_more_than_four_faces_for_one_panel(self):
        PanelFace.objects.create(
            panel=self.panel,
            code=PanelFace.FaceCode.A,
            monthly_price=Decimal("100000.00"),
        )
        PanelFace.objects.create(
            panel=self.panel,
            code=PanelFace.FaceCode.B,
            monthly_price=Decimal("100000.00"),
        )
        PanelFace.objects.create(
            panel=self.panel,
            code=PanelFace.FaceCode.C,
            monthly_price=Decimal("100000.00"),
        )
        PanelFace.objects.create(
            panel=self.panel,
            code=PanelFace.FaceCode.D,
            monthly_price=Decimal("100000.00"),
        )

        extra_face = PanelFace(
            panel=self.panel,
            code=PanelFace.FaceCode.A,
            monthly_price=Decimal("100000.00"),
        )

        with self.assertRaises(ValidationError):
            extra_face.full_clean()


class ReservationCreateViewTests(TestCase):
    def setUp(self):
        self.ouaga = City.objects.create(
            country_code="BF",
            name="Ouagadougou",
            slug="ouagadougou",
        )
        self.bobo = City.objects.create(
            country_code="BF",
            name="Bobo-Dioulasso",
            slug="bobo-dioulasso",
        )

        self.agency_a = Agency.objects.create(
            name="Agence A",
            slug="agence-a",
            email="a@test.com",
            country="BF",
            city_ref=self.ouaga,
        )
        self.agency_b = Agency.objects.create(
            name="Agence B",
            slug="agence-b",
            email="b@test.com",
            country="BF",
            city_ref=self.bobo,
        )

        self.super_admin = User.objects.create_user(
            username="superadmin2",
            password="testpass123",
            role=User.Role.SUPER_ADMIN,
            agency=self.agency_a,
        )
        self.manager = User.objects.create_user(
            username="manager",
            password="testpass123",
            role=User.Role.AGENCY_MANAGER,
            agency=self.agency_a,
        )

        self.panel_a = Panel.objects.create(
            agency=self.agency_a,
            reference="PANEL-A",
            format_category=Panel.FormatCategory.STANDARD,
            width_m=Decimal("4.00"),
            height_m=Decimal("3.00"),
            country="BF",
            city="Ouagadougou",
            city_ref=self.ouaga,
        )
        self.panel_b = Panel.objects.create(
            agency=self.agency_b,
            reference="PANEL-B",
            format_category=Panel.FormatCategory.LARGE,
            width_m=Decimal("6.00"),
            height_m=Decimal("4.00"),
            country="BF",
            city="Bobo-Dioulasso",
            city_ref=self.bobo,
        )

        self.face_a1 = PanelFace.objects.create(
            panel=self.panel_a,
            code=PanelFace.FaceCode.A,
            monthly_price=Decimal("100000.00"),
        )
        self.face_b1 = PanelFace.objects.create(
            panel=self.panel_b,
            code=PanelFace.FaceCode.A,
            monthly_price=Decimal("150000.00"),
        )

        self.client_obj = Client.objects.create(
            company_name="Client Test",
            contact_name="Contact Test",
            phone="70000000",
            email="client@test.com",
        )

    def test_super_admin_can_create_reservation_for_any_agency(self):
        self.client.login(username="superadmin2", password="testpass123")

        response = self.client.post(
            reverse("reservation_create"),
            {
                "agency": self.agency_b.id,
                "panel_face": self.face_b1.id,
                "client": self.client_obj.id,
                "source": Reservation.Source.PLATFORM,
                "status": Reservation.Status.PENDING,
                "start_date": "2026-04-01",
                "duration_months": "1",
                "monthly_price": "150000.00",
                "total_price": "150000.00",
                "need_design_help": "on",
                "notes": "Réservation super admin",
            },
        )

        self.assertRedirects(response, reverse("reservation_list"))
        reservation = Reservation.objects.get(notes="Réservation super admin")
        self.assertEqual(reservation.agency, self.agency_b)
        self.assertEqual(reservation.panel_face, self.face_b1)
        self.assertEqual(reservation.created_by, self.super_admin)
        self.assertEqual(reservation.end_date.isoformat(), "2026-04-30")

    def test_non_super_admin_is_forced_to_own_agency(self):
        self.client.login(username="manager", password="testpass123")

        response = self.client.post(
            reverse("reservation_create"),
            {
                "agency": self.agency_b.id,
                "panel_face": self.face_a1.id,
                "client": self.client_obj.id,
                "source": Reservation.Source.MANUAL,
                "status": Reservation.Status.PENDING,
                "start_date": "2026-05-01",
                "duration_months": "1",
                "monthly_price": "100000.00",
                "total_price": "100000.00",
                "notes": "Réservation manager",
            },
        )

        self.assertRedirects(response, reverse("reservation_list"))
        reservation = Reservation.objects.get(notes="Réservation manager")
        self.assertEqual(reservation.agency, self.agency_a)
        self.assertEqual(reservation.created_by, self.manager)

    def test_non_super_admin_form_shows_only_own_agency_faces(self):
        self.client.login(username="manager", password="testpass123")

        response = self.client.get(reverse("reservation_create"))

        self.assertEqual(response.status_code, 200)
        face_queryset = response.context["form"].fields["panel_face"].queryset
        self.assertEqual(list(face_queryset), [self.face_a1])

    def test_success_message_is_added_after_creation(self):
        self.client.login(username="manager", password="testpass123")

        response = self.client.post(
            reverse("reservation_create"),
            {
                "agency": self.agency_a.id,
                "panel_face": self.face_a1.id,
                "client": self.client_obj.id,
                "source": Reservation.Source.PLATFORM,
                "status": Reservation.Status.PENDING,
                "start_date": "2026-06-01",
                "duration_months": "1",
                "monthly_price": "100000.00",
                "total_price": "100000.00",
                "notes": "Réservation message",
            },
            follow=True,
        )

        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Réservation créée avec succès.", messages)

    def test_created_by_is_filled_automatically(self):
        self.client.login(username="manager", password="testpass123")

        self.client.post(
            reverse("reservation_create"),
            {
                "agency": self.agency_a.id,
                "panel_face": self.face_a1.id,
                "client": self.client_obj.id,
                "source": Reservation.Source.PLATFORM,
                "status": Reservation.Status.PENDING,
                "start_date": "2026-07-01",
                "duration_months": "1",
                "monthly_price": "100000.00",
                "total_price": "100000.00",
                "notes": "Réservation created_by",
            },
        )

        reservation = Reservation.objects.get(notes="Réservation created_by")
        self.assertEqual(reservation.created_by, self.manager)

    def test_monthly_price_and_total_price_are_auto_filled_when_blank(self):
        self.client.login(username="manager", password="testpass123")

        self.client.post(
            reverse("reservation_create"),
            {
                "agency": self.agency_a.id,
                "panel_face": self.face_a1.id,
                "client": self.client_obj.id,
                "source": Reservation.Source.PLATFORM,
                "status": Reservation.Status.PENDING,
                "start_date": "2026-08-01",
                "duration_months": "2",
                "monthly_price": "",
                "total_price": "",
                "notes": "Réservation auto prix",
            },
        )

        reservation = Reservation.objects.get(notes="Réservation auto prix")
        self.assertEqual(reservation.monthly_price, Decimal("100000.00"))
        self.assertEqual(reservation.total_price, Decimal("200000.00"))
        self.assertEqual(reservation.end_date.isoformat(), "2026-09-29")

    def test_panel_faces_api_filters_by_agency_and_period(self):
        Reservation.objects.create(
            agency=self.agency_a,
            panel_face=self.face_a1,
            client=self.client_obj,
            source=Reservation.Source.PLATFORM,
            status=Reservation.Status.APPROVED,
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 30),
            monthly_price=Decimal("100000.00"),
            total_price=Decimal("100000.00"),
            created_by=self.super_admin,
            notes="Blocage API",
        )

        self.client.login(username="superadmin2", password="testpass123")

        response = self.client.get(
            reverse("panel_faces_by_agency_api"),
            {
                "agency_id": self.agency_a.id,
                "start_date": "2026-09-01",
                "duration_months": "1",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["faces"], [])
        self.assertEqual(payload["computed_end_date"], "2026-09-30")