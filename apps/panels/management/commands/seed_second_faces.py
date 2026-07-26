import io
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFont

from apps.panels.models import Panel, PanelFace, PanelFaceImage


class Command(BaseCommand):
    help = (
        "Crée une deuxième face (Face B) pour chaque panneau qui n'en a qu'une, "
        "avec une image placeholder générée, pour illustrer la galerie multi-images."
    )

    def generate_placeholder_image(self, label, size=(800, 500), color=(60, 90, 150)):
        image = Image.new("RGB", size, color=color)
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except IOError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), label, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((size[0] - text_width) / 2, (size[1] - text_height) / 2)
        draw.text(position, label, fill=(255, 255, 255), font=font)

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)
        return buffer

    def handle(self, *args, **options):
        created_count = 0

        for panel in Panel.objects.prefetch_related("faces"):
            if panel.faces.count() >= 2:
                self.stdout.write(f"[{panel.reference}] déjà 2+ faces, ignoré.")
                continue

            existing_codes = set(panel.faces.values_list("code", flat=True))
            next_code = None
            for code in [PanelFace.FaceCode.B, PanelFace.FaceCode.C, PanelFace.FaceCode.D]:
                if code not in existing_codes:
                    next_code = code
                    break

            if next_code is None:
                self.stdout.write(self.style.WARNING(f"[{panel.reference}] déjà au maximum de faces."))
                continue

            face_a = panel.faces.filter(code=PanelFace.FaceCode.A).first()
            monthly_price = face_a.monthly_price if face_a else Decimal("100000.00")

            face = PanelFace.objects.create(
                panel=panel,
                code=next_code,
                orientation="Vue opposée",
                monthly_price=monthly_price,
                operational_status=PanelFace.OperationalStatus.AVAILABLE,
            )

            buffer = self.generate_placeholder_image(f"{panel.reference} - Face {next_code}")
            image = PanelFaceImage(
                face=face,
                caption="panel-placeholder-2",
                is_primary=True,
                display_order=0,
            )
            image.image.save(
                "panel-placeholder-2.jpg",
                ContentFile(buffer.read()),
                save=True,
            )

            created_count += 1
            self.stdout.write(self.style.SUCCESS(f"[{panel.reference}] Face {next_code} créée avec image."))

        self.stdout.write(self.style.SUCCESS(f"{created_count} face(s) créée(s)."))