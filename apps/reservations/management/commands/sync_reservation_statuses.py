from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.reservations.models import Reservation, ReservationStatusLog


class Command(BaseCommand):
    help = "Synchronise automatiquement les statuts des réservations expirées."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche les réservations concernées sans les modifier.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        today = timezone.localdate()

        reservations_to_complete = Reservation.objects.select_related(
            "agency",
            "panel_face__panel",
            "client",
        ).filter(
            status=Reservation.Status.ACTIVE,
            end_date__lt=today,
        ).order_by("end_date", "id")

        count = reservations_to_complete.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS("Aucune réservation active expirée à synchroniser.")
            )
            return

        self.stdout.write(
            f"{count} réservation(s) active(s) expirée(s) trouvée(s)."
        )

        for reservation in reservations_to_complete:
            self.stdout.write(
                f"- Reservation #{reservation.id} | "
                f"Panel {reservation.panel_face.panel.reference} | "
                f"Face {reservation.panel_face.code} | "
                f"Fin: {reservation.end_date}"
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Mode dry-run activé : aucune modification effectuée.")
            )
            return

        updated_count = 0

        with transaction.atomic():
            for reservation in reservations_to_complete:
                old_status = reservation.status
                reservation.status = Reservation.Status.COMPLETED
                reservation.save()

                ReservationStatusLog.objects.create(
                    reservation=reservation,
                    old_status=old_status,
                    new_status=Reservation.Status.COMPLETED,
                    changed_by=None,
                    note="Synchronisation automatique : fin de période atteinte.",
                )
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Synchronisation terminée : {updated_count} réservation(s) passée(s) à COMPLETED."
            )
        )