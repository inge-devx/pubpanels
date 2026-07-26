import openpyxl

from apps.panels.models import Panel


def _get_cell_background(cell):
    fill = cell.fill
    if fill is None or fill.fill_type != "solid":
        return None

    fg = fill.fgColor
    if fg is None or fg.type != "rgb" or not fg.rgb:
        return None

    rgb = fg.rgb
    if not isinstance(rgb, str) or len(rgb) != 8:
        return None

    hex_color = f"#{rgb[2:]}"
    if hex_color.upper() in ("#FFFFFF", "#000000"):
        return None

    return hex_color


def parse_excel_grid(uploaded_file):
    """Retourne la grille brute complète du fichier : liste de lignes,
    chaque ligne étant une liste de {'v': valeur, 'bg': couleur ou None}."""
    workbook = openpyxl.load_workbook(uploaded_file, data_only=True)
    sheet = workbook.active

    grid = []
    for row in sheet.iter_rows():
        cells = []
        has_content = False
        for cell in row:
            value = "" if cell.value is None else str(cell.value).strip()
            if value:
                has_content = True
            cells.append({"v": value, "bg": _get_cell_background(cell)})
        if has_content:
            grid.append(cells)

    return grid


def get_agency_initials(agency):
    words = [w for w in agency.name.split() if w.isalpha()]
    if not words:
        return "PAN"
    initials = "".join(w[0] for w in words).upper()
    return initials[:6] or "PAN"


def suggest_next_reference(batch):
    prefix = batch.reference_prefix or "PAN"
    number = batch.next_reference_number

    while True:
        candidate = f"{prefix}-{number:03d}"
        exists = Panel.objects.filter(agency=batch.agency, reference=candidate).exists()
        if not exists:
            return candidate, number
        number += 1