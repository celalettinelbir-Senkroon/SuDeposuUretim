from decimal import Decimal

WALL_MODULE_HEIGHT_M = Decimal("0.5")
FULL_PANEL_WIDTH_MM = Decimal("1080")
FULL_PANEL_LENGTH_MM = Decimal("1080")
HALF_PANEL_WIDTH_MM = Decimal("540")
HALF_PANEL_LENGTH_MM = Decimal("1080")
QUARTER_PANEL_WIDTH_MM = Decimal("540")
QUARTER_PANEL_LENGTH_MM = Decimal("540")
MODULE_MM = Decimal("1080")

ZONE_CATEGORY_MAPPING = {
    "WALL": "duvar_paneli",
    "BASE": "duz_taban_paneli",
    "ROOF": "tavan_paneli",
    "COVER": "kapakli_duvar_paneli",
    "ACCESSORY": "aksesuar",
    "EXTERNAL_ANGLE": "dis_kosebent",
    "INTERNAL_TIE": "ic_gergi",
}
