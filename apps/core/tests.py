from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.agencies.models import Agency
from apps.locations.models import City
from apps.panels.models import Panel, PanelFace, PanelImage
from apps.reservations.models import Client, Reservation
from apps.users.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile



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

class PanelMapAndImagesTests(TestCase):
    def setUp(self):
        self.ouaga = City.objects.create(
            country_code="BF",
            name="Ouagadougou",
            slug="ouagadougou",
        )

        self.agency = Agency.objects.create(
            name="Agence Images",
            slug="agence-images",
            status=Agency.Status.ACTIVE,
            country="BF",
            city_ref=self.ouaga,
            email="images@test.com",
        )

        self.super_admin = User.objects.create_user(
            username="super_images",
            password="testpass123",
            role=User.Role.SUPER_ADMIN,
            agency=self.agency,
        )

        self.panel = Panel.objects.create(
            agency=self.agency,
            reference="IMG-PANEL-001",
            format_category=Panel.FormatCategory.STANDARD,
            width_m=Decimal("4.00"),
            height_m=Decimal("3.00"),
            country="BF",
            city="Ouagadougou",
            city_ref=self.ouaga,
            latitude=Decimal("12.371430"),
            longitude=Decimal("-1.519660"),
            is_published=True,
        )

    def test_panel_generates_google_maps_url_from_coordinates(self):
        self.assertEqual(
            self.panel.google_maps_url,
            "https://www.google.com/maps?q=12.371430,-1.519660",
        )

    def test_public_panel_detail_shows_google_maps_link(self):
        response = self.client.get(
            reverse("public_panel_detail", args=[self.panel.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Voir sur la carte")
        self.assertContains(
            response,
            "https://www.google.com/maps?q=12.371430,-1.519660",
        )

    def test_backoffice_panel_detail_shows_google_maps_link(self):
        self.client.login(username="super_images", password="testpass123")

        response = self.client.get(
            reverse("panel_detail", args=[self.panel.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Voir sur la carte")
        self.assertContains(
            response,
            "https://www.google.com/maps?q=12.371430,-1.519660",
        )

    def test_panel_accepts_primary_image(self):
        image_file = SimpleUploadedFile(
            "panel.jpg",
            b"fake-image-content",
            content_type="image/jpeg",
        )

        panel_image = self.panel.images.create(
            image=image_file,
            image_type=PanelImage.ImageType.FACE,
            caption="Vue de face",
            is_primary=True,
            display_order=1,
        )

        self.assertEqual(panel_image.panel, self.panel)
        self.assertTrue(panel_image.is_primary)

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

class ReservationEmailNotificationTests(TestCase):
    def setUp(self):
        self.ouaga = City.objects.create(
            country_code="BF",
            name="Ouagadougou",
            slug="ouagadougou",
        )

        self.agency = Agency.objects.create(
            name="Agence Email",
            slug="agence-email",
            status=Agency.Status.ACTIVE,
            country="BF",
            city_ref=self.ouaga,
            email="agency@test.com",
        )

        self.manager = User.objects.create_user(
            username="manager_email",
            password="testpass123",
            role=User.Role.AGENCY_MANAGER,
            agency=self.agency,
        )

        self.panel = Panel.objects.create(
            agency=self.agency,
            reference="EMAIL-PANEL-001",
            format_category=Panel.FormatCategory.STANDARD,
            width_m=Decimal("4.00"),
            height_m=Decimal("3.00"),
            country="BF",
            city="Ouagadougou",
            city_ref=self.ouaga,
            is_published=True,
        )

        self.face_a = PanelFace.objects.create(
            panel=self.panel,
            code=PanelFace.FaceCode.A,
            monthly_price=Decimal("100000.00"),
            operational_status=PanelFace.OperationalStatus.AVAILABLE,
        )

        self.client_obj = Client.objects.create(
            company_name="Client Email",
            contact_name="Jean Email",
            phone="70222222",
            email="client-email@test.com",
        )

    def test_public_request_sends_internal_email_to_agency(self):
        response = self.client.post(
            reverse("public_reservation_request_for_panel", args=[self.panel.id]),
            {
                "company_name": "Entreprise Email",
                "contact_name": "Jean Email",
                "phone": "70222222",
                "email": "client-email@test.com",
                "business_sector": "Commerce",
                "panel_face": self.face_a.id,
                "start_date": "2026-10-01",
                "duration_months": "1",
                "notes": "Demande email",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("public_reservation_success"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Nouvelle demande de réservation", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ["agency@test.com"])

    def test_status_change_sends_email_to_client(self):
        reservation = Reservation.objects.create(
            agency=self.agency,
            panel_face=self.face_a,
            client=self.client_obj,
            source=Reservation.Source.PLATFORM,
            status=Reservation.Status.PENDING,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 30),
            monthly_price=Decimal("100000.00"),
            total_price=Decimal("100000.00"),
            created_by=self.manager,
        )

        self.client.login(username="manager_email", password="testpass123")


        mail.outbox.clear()
        self.client.post(
            reverse("reservation_change_status", args=[reservation.id, "approved"]),
            follow=True,
        )

        self.assertGreaterEqual(len(mail.outbox), 1)

        matching_emails = [
            email for email in mail.outbox
            if "Mise à jour de votre réservation" in email.subject
               and email.to == ["client-email@test.com"]
        ]

        self.assertEqual(len(matching_emails), 1)

    def test_no_internal_email_sent_if_agency_email_missing(self):
        self.agency.email = ""
        self.agency.save()

        response = self.client.post(
            reverse("public_reservation_request_for_panel", args=[self.panel.id]),
            {
                "company_name": "Entreprise Sans Email",
                "contact_name": "Jean Sans Email",
                "phone": "70333333",
                "email": "client2@test.com",
                "business_sector": "Commerce",
                "panel_face": self.face_a.id,
                "start_date": "2026-11-01",
                "duration_months": "1",
                "notes": "Aucun email agence",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("public_reservation_success"))
        self.assertEqual(len(mail.outbox), 0)

    def test_no_client_email_sent_if_client_email_missing(self):
        self.client_obj.email = ""
        self.client_obj.save()

        reservation = Reservation.objects.create(
            agency=self.agency,
            panel_face=self.face_a,
            client=self.client_obj,
            source=Reservation.Source.PLATFORM,
            status=Reservation.Status.PENDING,
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 30),
            monthly_price=Decimal("100000.00"),
            total_price=Decimal("100000.00"),
            created_by=self.manager,
        )

        self.client.login(username="manager_email", password="testpass123")

        self.client.post(
            reverse("reservation_change_status", args=[reservation.id, "approved"]),
            follow=True,
        )

        self.assertEqual(len(mail.outbox), 0)

class ReservationBackofficeWorkflowTests(TestCase):
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
            slug="agence-a-wf",
            status=Agency.Status.ACTIVE,
            country="BF",
            city_ref=self.ouaga,
        )
        self.agency_b = Agency.objects.create(
            name="Agence B",
            slug="agence-b-wf",
            status=Agency.Status.ACTIVE,
            country="BF",
            city_ref=self.bobo,
        )

        self.super_admin = User.objects.create_user(
            username="superadmin_wf",
            password="testpass123",
            role=User.Role.SUPER_ADMIN,
            agency=self.agency_a,
        )
        self.manager_a = User.objects.create_user(
            username="manager_a_wf",
            password="testpass123",
            role=User.Role.AGENCY_MANAGER,
            agency=self.agency_a,
        )
        self.manager_b = User.objects.create_user(
            username="manager_b_wf",
            password="testpass123",
            role=User.Role.AGENCY_MANAGER,
            agency=self.agency_b,
        )

        self.panel_a = Panel.objects.create(
            agency=self.agency_a,
            reference="WF-PANEL-A",
            format_category=Panel.FormatCategory.STANDARD,
            width_m=Decimal("4.00"),
            height_m=Decimal("3.00"),
            country="BF",
            city="Ouagadougou",
            city_ref=self.ouaga,
            is_published=True,
        )
        self.panel_b = Panel.objects.create(
            agency=self.agency_b,
            reference="WF-PANEL-B",
            format_category=Panel.FormatCategory.LARGE,
            width_m=Decimal("6.00"),
            height_m=Decimal("4.00"),
            country="BF",
            city="Bobo-Dioulasso",
            city_ref=self.bobo,
            is_published=True,
        )

        self.face_a = PanelFace.objects.create(
            panel=self.panel_a,
            code=PanelFace.FaceCode.A,
            monthly_price=Decimal("100000.00"),
        )
        self.face_b = PanelFace.objects.create(
            panel=self.panel_b,
            code=PanelFace.FaceCode.A,
            monthly_price=Decimal("150000.00"),
        )

        self.client_obj = Client.objects.create(
            company_name="Client Workflow",
            contact_name="Contact Workflow",
            phone="70000010",
            email="workflow@test.com",
        )

        self.reservation = Reservation.objects.create(
            agency=self.agency_a,
            panel_face=self.face_a,
            client=self.client_obj,
            source=Reservation.Source.PLATFORM,
            status=Reservation.Status.PENDING,
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 30),
            monthly_price=Decimal("100000.00"),
            total_price=Decimal("100000.00"),
            created_by=None,
            notes="Demande workflow",
        )

    def test_super_admin_can_view_reservation_detail(self):
        self.client.login(username="superadmin_wf", password="testpass123")

        response = self.client.get(reverse("reservation_detail", args=[self.reservation.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Demande workflow")
        self.assertContains(response, "Client Workflow")

    def test_agency_user_can_view_own_reservation_detail(self):
        self.client.login(username="manager_a_wf", password="testpass123")

        response = self.client.get(reverse("reservation_detail", args=[self.reservation.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WF-PANEL-A")

    def test_agency_user_cannot_view_other_agency_reservation_detail(self):
        self.client.login(username="manager_b_wf", password="testpass123")

        response = self.client.get(reverse("reservation_detail", args=[self.reservation.id]))

        self.assertEqual(response.status_code, 404)

    def test_agency_user_can_update_own_reservation(self):
        self.client.login(username="manager_a_wf", password="testpass123")

        response = self.client.post(
            reverse("reservation_update", args=[self.reservation.id]),
            {
                "panel_face": self.face_a.id,
                "client": self.client_obj.id,
                "start_date": "2026-11-01",
                "duration_months": "2",
                "monthly_price": "100000.00",
                "total_price": "200000.00",
                "need_design_help": "on",
                "notes": "Mise à jour workflow",
            },
        )

        self.reservation.refresh_from_db()
        self.assertRedirects(response, reverse("reservation_detail", args=[self.reservation.id]))
        self.assertEqual(self.reservation.start_date.isoformat(), "2026-11-01")
        self.assertEqual(self.reservation.end_date.isoformat(), "2026-12-30")
        self.assertEqual(self.reservation.total_price, Decimal("200000.00"))
        self.assertEqual(self.reservation.notes, "Mise à jour workflow")

    def test_active_reservation_cannot_be_opened_for_update(self):
        self.reservation.status = Reservation.Status.ACTIVE
        self.reservation.save()

        self.client.login(username="manager_a_wf", password="testpass123")

        response = self.client.get(
            reverse("reservation_update", args=[self.reservation.id]),
            follow=True,
        )

        self.assertRedirects(response, reverse("reservation_detail", args=[self.reservation.id]))
        self.assertContains(response, "Cette réservation ne peut plus être modifiée")

    def test_completed_reservation_cannot_be_opened_for_update(self):
        self.reservation.status = Reservation.Status.COMPLETED
        self.reservation.save()

        self.client.login(username="manager_a_wf", password="testpass123")

        response = self.client.get(
            reverse("reservation_update", args=[self.reservation.id]),
            follow=True,
        )

        self.assertRedirects(response, reverse("reservation_detail", args=[self.reservation.id]))
        self.assertContains(response, "Cette réservation ne peut plus être modifiée")

    def test_agency_user_cannot_update_other_agency_reservation(self):
        self.client.login(username="manager_b_wf", password="testpass123")

        response = self.client.get(reverse("reservation_update", args=[self.reservation.id]))

        self.assertEqual(response.status_code, 404)

    def test_pending_can_be_approved(self):
        self.client.login(username="manager_a_wf", password="testpass123")

        response = self.client.post(
            reverse("reservation_change_status", args=[self.reservation.id, "approved"]),
            follow=True,
        )

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.Status.APPROVED)
        messages_list = [m.message for m in get_messages(response.wsgi_request)]
        self.assertTrue(any("Approved" in msg or "Approuv" in msg for msg in messages_list))

    def test_approved_can_be_activated(self):
        self.reservation.status = Reservation.Status.APPROVED
        self.reservation.save()

        self.client.login(username="manager_a_wf", password="testpass123")

        self.client.post(reverse("reservation_change_status", args=[self.reservation.id, "active"]))

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.Status.ACTIVE)

    def test_active_can_be_completed(self):
        self.reservation.status = Reservation.Status.ACTIVE
        self.reservation.save()

        self.client.login(username="manager_a_wf", password="testpass123")

        self.client.post(reverse("reservation_change_status", args=[self.reservation.id, "completed"]))

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.Status.COMPLETED)

    def test_invalid_transition_is_rejected(self):
        self.reservation.status = Reservation.Status.PENDING
        self.reservation.save()

        self.client.login(username="manager_a_wf", password="testpass123")

        self.client.post(reverse("reservation_change_status", args=[self.reservation.id, "completed"]))

        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, Reservation.Status.PENDING)

    def test_reservation_list_can_filter_by_status(self):
        self.client.login(username="manager_a_wf", password="testpass123")

        response = self.client.get(reverse("reservation_list"), {"status": Reservation.Status.PENDING})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WF-PANEL-A")

    def test_status_change_creates_log(self):
        self.client.login(username="manager_a_wf", password="testpass123")

        self.client.post(
            reverse("reservation_change_status", args=[self.reservation.id, "approved"])
        )

        from apps.reservations.models import ReservationStatusLog

        log = ReservationStatusLog.objects.get(reservation=self.reservation)

        self.assertEqual(log.old_status, Reservation.Status.PENDING)
        self.assertEqual(log.new_status, Reservation.Status.APPROVED)
        self.assertEqual(log.changed_by.username, "manager_a_wf")

class DashboardBusinessMetricsTests(TestCase):
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
            name="Agence Dashboard A",
            slug="agence-dashboard-a",
            email="a@test.com",
            status=Agency.Status.ACTIVE,
            country="BF",
            city_ref=self.ouaga,
        )
        self.agency_b = Agency.objects.create(
            name="Agence Dashboard B",
            slug="agence-dashboard-b",
            email="b@test.com",
            status=Agency.Status.ACTIVE,
            country="BF",
            city_ref=self.bobo,
        )

        self.super_admin = User.objects.create_user(
            username="super_dashboard",
            password="testpass123",
            role=User.Role.SUPER_ADMIN,
            agency=self.agency_a,
        )
        self.manager_a = User.objects.create_user(
            username="manager_dashboard_a",
            password="testpass123",
            role=User.Role.AGENCY_MANAGER,
            agency=self.agency_a,
        )

        self.panel_a = Panel.objects.create(
            agency=self.agency_a,
            reference="DASH-PANEL-A",
            format_category=Panel.FormatCategory.STANDARD,
            width_m=Decimal("4.00"),
            height_m=Decimal("3.00"),
            country="BF",
            city="Ouagadougou",
            city_ref=self.ouaga,
            is_published=True,
        )
        self.panel_b = Panel.objects.create(
            agency=self.agency_b,
            reference="DASH-PANEL-B",
            format_category=Panel.FormatCategory.LARGE,
            width_m=Decimal("6.00"),
            height_m=Decimal("4.00"),
            country="BF",
            city="Bobo-Dioulasso",
            city_ref=self.bobo,
            is_published=True,
        )

        self.face_a1 = PanelFace.objects.create(
            panel=self.panel_a,
            code=PanelFace.FaceCode.A,
            monthly_price=Decimal("100000.00"),
        )
        self.face_a2 = PanelFace.objects.create(
            panel=self.panel_a,
            code=PanelFace.FaceCode.B,
            monthly_price=Decimal("120000.00"),
        )
        self.face_b1 = PanelFace.objects.create(
            panel=self.panel_b,
            code=PanelFace.FaceCode.A,
            monthly_price=Decimal("150000.00"),
        )

        self.client_1 = Client.objects.create(
            company_name="Client A",
            contact_name="Contact A",
            phone="70010001",
            email="a@test.com",
        )
        self.client_2 = Client.objects.create(
            company_name="Client B",
            contact_name="Contact B",
            phone="70010002",
            email="b@test.com",
        )

        today = date.today()

        self.pending_reservation = Reservation.objects.create(
            agency=self.agency_a,
            panel_face=self.face_a1,
            client=self.client_1,
            source=Reservation.Source.PLATFORM,
            status=Reservation.Status.PENDING,
            start_date=today,
            end_date=today + timedelta(days=30),
            monthly_price=Decimal("100000.00"),
            total_price=Decimal("100000.00"),
            created_by=self.manager_a,
            notes="Pending reservation",
        )

        self.active_reservation = Reservation.objects.create(
            agency=self.agency_a,
            panel_face=self.face_a2,
            client=self.client_2,
            source=Reservation.Source.PLATFORM,
            status=Reservation.Status.ACTIVE,
            start_date=today - timedelta(days=25),
            end_date=today + timedelta(days=4),  # >= 30 jours
            monthly_price=Decimal("120000.00"),
            total_price=Decimal("120000.00"),
            created_by=self.manager_a,
            notes="Active reservation",
        )

        self.completed_reservation = Reservation.objects.create(
            agency=self.agency_b,
            panel_face=self.face_b1,
            client=self.client_1,
            source=Reservation.Source.PLATFORM,
            status=Reservation.Status.COMPLETED,
            start_date=today - timedelta(days=40),
            end_date=today - timedelta(days=10),
            monthly_price=Decimal("150000.00"),
            total_price=Decimal("150000.00"),
            created_by=self.super_admin,
            notes="Completed reservation",
        )

    def test_super_admin_dashboard_shows_global_metrics(self):
        self.client.login(username="super_dashboard", password="testpass123")

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)

        # Vérification métier via le context
        self.assertEqual(response.context["panel_count"], 2)
        self.assertEqual(response.context["reservation_count"], 3)
        self.assertEqual(response.context["pending_count"], 1)
        self.assertEqual(response.context["active_count"], 1)
        self.assertEqual(response.context["completed_count"], 1)
        self.assertEqual(response.context["total_faces_count"], 3)
        self.assertEqual(response.context["occupied_faces_count"], 1)
        self.assertEqual(response.context["available_faces_count"], 2)

        self.assertEqual(str(response.context["total_revenue"]), "370000.00")
        self.assertEqual(str(response.context["committed_revenue"]), "120000.00")
        self.assertEqual(str(response.context["active_revenue"]), "120000.00")
        self.assertEqual(str(response.context["completed_revenue"]), "150000.00")

        # Vérifications minimales de rendu
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "DASH-PANEL-A")
        self.assertContains(response, "DASH-PANEL-B")

    def test_agency_manager_dashboard_is_scoped_to_own_agency(self):
        self.client.login(username="manager_dashboard_a", password="testpass123")

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)

        # Vérification métier via le context
        self.assertEqual(response.context["panel_count"], 1)
        self.assertEqual(response.context["reservation_count"], 2)
        self.assertEqual(response.context["pending_count"], 1)
        self.assertEqual(response.context["active_count"], 1)
        self.assertEqual(response.context["completed_count"], 0)
        self.assertEqual(response.context["total_faces_count"], 2)
        self.assertEqual(response.context["occupied_faces_count"], 1)
        self.assertEqual(response.context["available_faces_count"], 1)

        self.assertEqual(str(response.context["total_revenue"]), "220000.00")
        self.assertEqual(str(response.context["committed_revenue"]), "120000.00")
        self.assertEqual(str(response.context["active_revenue"]), "120000.00")
        self.assertEqual(str(response.context["completed_revenue"]), "0.00")

        # Vérifications minimales de rendu / scope
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "DASH-PANEL-A")
        self.assertNotContains(response, "DASH-PANEL-B")

    def test_dashboard_shows_upcoming_endings(self):
        self.client.login(username="manager_dashboard_a", password="testpass123")

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Réservations qui se terminent bientôt")
        self.assertContains(response, "DASH-PANEL-A")
        self.assertContains(response, "Client B - Contact B")
        self.assertContains(response, f'/reservations/{self.active_reservation.id}/')


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

        future_start = timezone.localdate() + timedelta(days=7)
        expected_end = future_start + timedelta(days=29)

        response = self.client.post(
            reverse("reservation_create"),
            {
                "agency": self.agency_b.id,
                "panel_face": self.face_b1.id,
                "client": self.client_obj.id,
                "source": Reservation.Source.PLATFORM,
                "status": Reservation.Status.PENDING,
                "start_date": future_start.isoformat(),
                "duration_months": "1",
                "monthly_price": "150000.00",
                "total_price": "150000.00",
                "need_design_help": "on",
                "notes": "Réservation super admin",
            },
        )

        reservation = Reservation.objects.get(notes="Réservation super admin")
        self.assertRedirects(response, reverse("reservation_detail", args=[reservation.id]))
        self.assertEqual(reservation.agency, self.agency_b)
        self.assertEqual(reservation.panel_face, self.face_b1)
        self.assertEqual(reservation.created_by, self.super_admin)
        self.assertEqual(reservation.end_date, expected_end)

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

        reservation = Reservation.objects.get(notes="Réservation manager")
        self.assertRedirects(response, reverse("reservation_detail", args=[reservation.id]))
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