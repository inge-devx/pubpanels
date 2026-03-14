from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from apps.agencies.models import Agency
from apps.panels.models import Panel
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

        self.assertRedirects(response, reverse("panel_list"))
        panel = Panel.objects.get(reference="PNL-SUP-001")
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

        self.assertRedirects(response, reverse("panel_list"))
        panel = Panel.objects.get(reference="PNL-MNG-001")
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
