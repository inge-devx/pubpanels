from datetime import date
from decimal import Decimal

from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.agencies.models import Agency
from apps.panels.models import Panel, PanelFace
from apps.reservations.models import Client, Reservation
from apps.users.models import User


class PanelCreateViewTests(TestCase):
    def setUp(self):
        self.agency_a = Agency.objects.create(
            name="Agence A",
            slug="agence-a",
            email="a@test.com",
        )
        self.agency_b = Agency.objects.create(
            name="Agence B",
            slug="agence-b",
            email="b@test.com",
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
                "format": "12x4",
                "city": "Ouagadougou",
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

    def test_non_super_admin_is_forced_to_own_agency(self):
        self.client.login(username="manager", password="testpass123")

        response = self.client.post(
            reverse("panel_create"),
            {
                "agency": self.agency_b.id,
                "reference": "PNL-MNG-001",
                "title": "Panneau manager",
                "format": "4x3",
                "city": "Bobo-Dioulasso",
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
                "format": "12x4",
                "city": "Ouaga",
                "status": Panel.Status.ACTIVE,
                "is_published": "on",
            },
            follow=True,
        )

        messages = [m.message for m in get_messages(response.wsgi_request)]
        self.assertIn("Panneau créé avec succès.", messages)


class PanelDetailAndUpdateViewTests(TestCase):
    def setUp(self):
        self.agency_a = Agency.objects.create(
            name="Agence A",
            slug="agence-a",
            email="a@test.com",
        )
        self.agency_b = Agency.objects.create(
            name="Agence B",
            slug="agence-b",
            email="b@test.com",
        )

        self.super_admin = User.objects.create_user(
            username="superadmin",
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
            format="12x4",
            city="Ouagadougou",
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
        self.client.login(username="superadmin", password="testpass123")

        response = self.client.get(reverse("panel_detail", args=[self.panel_a.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PANEL-A")
        self.assertContains(response, "Panneau A")

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
        self.client.login(username="superadmin", password="testpass123")

        response = self.client.post(
            reverse("panel_update", args=[self.panel_a.id]),
            {
                "agency": self.agency_b.id,
                "reference": "PANEL-A-UPDATED",
                "title": "Panneau modifié",
                "format": "4x3",
                "city": "Bobo-Dioulasso",
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
        self.assertEqual(self.panel_a.title, "Panneau modifié")

    def test_agency_user_is_forced_to_keep_own_agency_on_update(self):
        self.client.login(username="managera", password="testpass123")

        response = self.client.post(
            reverse("panel_update", args=[self.panel_a.id]),
            {
                "agency": self.agency_b.id,
                "reference": "PANEL-A-UPDATED-2",
                "title": "Panneau agence",
                "format": "12x4",
                "city": "Ouagadougou",
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
        self.assertEqual(self.panel_a.reference, "PANEL-A-UPDATED-2")

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
                "format": "12x4",
                "city": "Ouagadougou",
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
        self.agency = Agency.objects.create(
            name="Agence Test",
            slug="agence-test",
            email="agence@test.com",
        )
        self.panel = Panel.objects.create(
            agency=self.agency,
            reference="PANEL-FACES",
            format="12x4",
            city="Ouagadougou",
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
        self.agency_a = Agency.objects.create(
            name="Agence A",
            slug="agence-a",
            email="a@test.com",
        )
        self.agency_b = Agency.objects.create(
            name="Agence B",
            slug="agence-b",
            email="b@test.com",
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
            format="12x4",
            city="Ouagadougou",
        )
        self.panel_b = Panel.objects.create(
            agency=self.agency_b,
            reference="PANEL-B",
            format="12x4",
            city="Bobo-Dioulasso",
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