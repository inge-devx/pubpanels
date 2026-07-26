from django.conf import settings
from django.core.mail import send_mail

from .models import Reservation


def _safe_recipient_list(*emails):
    recipients = []
    for email in emails:
        if email and isinstance(email, str) and email.strip():
            recipients.append(email.strip())
    return recipients


def send_new_public_reservation_notification(reservation: Reservation) -> int:
    """
    Notifie l'agence qu'une nouvelle demande publique de réservation a été créée.
    Retourne le nombre d'emails envoyés.
    """
    agency_email = reservation.agency.email
    recipients = _safe_recipient_list(agency_email)

    if not recipients:
        return 0

    subject = f"Nouvelle demande de réservation - {reservation.panel_face.panel.reference}"
    body = (
        "Une nouvelle demande publique de réservation a été enregistrée.\n\n"
        f"Agence : {reservation.agency.name}\n"
        f"Panneau : {reservation.panel_face.panel.reference}\n"
        f"Face : {reservation.panel_face.code}\n"
        f"Client : {reservation.client}\n"
        f"Téléphone : {reservation.client.phone}\n"
        f"Email : {reservation.client.email or '—'}\n"
        f"Date de début : {reservation.start_date}\n"
        f"Date de fin : {reservation.end_date}\n"
        f"Prix mensuel : {reservation.monthly_price}\n"
        f"Prix total : {reservation.total_price}\n"
        f"Besoin design : {'Oui' if reservation.need_design_help else 'Non'}\n"
        f"Notes : {reservation.notes or '—'}\n"
    )

    return send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=False,
    )


def send_client_reservation_status_notification(reservation: Reservation) -> int:
    """
    Notifie le client lors d'un changement de statut pertinent.
    Retourne le nombre d'emails envoyés.
    """
    client_email = reservation.client.email
    recipients = _safe_recipient_list(client_email)

    if not recipients:
        return 0

    status_labels = {
        Reservation.Status.PENDING: "en attente",
        Reservation.Status.APPROVED: "approuvée",
        Reservation.Status.ACTIVE: "active",
        Reservation.Status.COMPLETED: "terminée",
        Reservation.Status.REJECTED: "rejetée",
        Reservation.Status.CANCELLED: "annulée",
    }

    readable_status = status_labels.get(reservation.status, reservation.status)

    subject = f"Mise à jour de votre réservation - {reservation.panel_face.panel.reference}"
    body = (
        f"Bonjour {reservation.client.contact_name},\n\n"
        "Le statut de votre demande de réservation a été mis à jour.\n\n"
        f"Statut actuel : {readable_status}\n"
        f"Panneau : {reservation.panel_face.panel.reference}\n"
        f"Face : {reservation.panel_face.code}\n"
        f"Date de début : {reservation.start_date}\n"
        f"Date de fin : {reservation.end_date}\n"
        f"Agence : {reservation.agency.name}\n\n"
        "Merci."
    )

    return send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=False,
    )