from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.agencies.models import Agency
from apps.panels.models import Panel, PanelFace
from apps.reservations.models import Client, Reservation
from apps.users.models import User


class ReservationModelTests(TestCase):
    def setUp(self):
        self.agency = Agency.objects.create(
            name="Agence Test",
            slug="agence-test",
            email="agence@test.com",
        )

        self.user = User.objects.create_user(
            username="manager1",
            password="testpass123",
            role=User.Role.AGENCY_MANAGER,
            agency=self.agency,
        )

        self.panel = Panel.objects.create(
            agency=self.agency,
            reference="PANEL-001",
            format="12x4",
            city="Ouagadougou",
        )

        self.face_a = PanelFace.objects.create(
            panel=self.panel,
            code=PanelFace.FaceCode.A,
            monthly_price=Decimal("100000.00"),
        )

        self.client = Client.objects.create(
            company_name="Client SARL",
            contact_name="Ali Test",
            phone="70000000",
            email="client@test.com",
        )

    def test_blocking_reservation_overlap_is_rejected(self):
        Reservation.objects.create(
            agency=self.agency,
            panel_face=self.face_a,
            client=self.client,
            source=Reservation.Source.PLATFORM,
            status=Reservation.Status.APPROVED,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
            monthly_price=Decimal("100000.00"),
            total_price=Decimal("100000.00"),
            created_by=self.user,
        )

        reservation = Reservation(
            agency=self.agency,
            panel_face=self.face_a,
            client=self.client,
            source=Reservation.Source.PLATFORM,
            status=Reservation.Status.APPROVED,
            start_date=date(2026, 3, 15),
            end_date=date(2026, 4, 15),
            monthly_price=Decimal("100000.00"),
            total_price=Decimal("100000.00"),
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            reservation.full_clean()

    def test_pending_overlap_is_allowed(self):
        Reservation.objects.create(
            agency=self.agency,
            panel_face=self.face_a,
            client=self.client,
            source=Reservation.Source.PLATFORM,
            status=Reservation.Status.APPROVED,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
            monthly_price=Decimal("100000.00"),
            total_price=Decimal("100000.00"),
            created_by=self.user,
        )

        reservation = Reservation(
            agency=self.agency,
            panel_face=self.face_a,
            client=self.client,
            source=Reservation.Source.PLATFORM,
            status=Reservation.Status.PENDING,
            start_date=date(2026, 3, 15),
            end_date=date(2026, 4, 15),
            monthly_price=Decimal("100000.00"),
            total_price=Decimal("100000.00"),
            created_by=self.user,
        )

        reservation.full_clean()  # ne doit pas lever d'erreur

    def test_end_date_before_start_date_is_rejected(self):
        reservation = Reservation(
            agency=self.agency,
            panel_face=self.face_a,
            client=self.client,
            source=Reservation.Source.PLATFORM,
            status=Reservation.Status.PENDING,
            start_date=date(2026, 4, 10),
            end_date=date(2026, 4, 1),
            monthly_price=Decimal("100000.00"),
            total_price=Decimal("100000.00"),
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            reservation.full_clean()

    def test_panel_face_must_belong_to_selected_agency(self):
        other_agency = Agency.objects.create(
            name="Autre Agence",
            slug="autre-agence",
            email="autre@test.com",
        )

        reservation = Reservation(
            agency=other_agency,
            panel_face=self.face_a,
            client=self.client,
            source=Reservation.Source.PLATFORM,
            status=Reservation.Status.PENDING,
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
            monthly_price=Decimal("100000.00"),
            total_price=Decimal("100000.00"),
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            reservation.full_clean()