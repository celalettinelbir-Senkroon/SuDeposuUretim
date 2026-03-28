from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR
from .constants import (
    WALL_MODULE_HEIGHT_M,
    ZONE_CATEGORY_MAPPING
)

def _to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None

def _get_panel_type_name(panel_width_m, panel_length_m):
    w = panel_width_m
    l = panel_length_m
    if w == Decimal("1.0") and l == Decimal("1.0"):
        return "FULL"
    elif (w == Decimal("0.5") and l == Decimal("1.0")) or (w == Decimal("1.0") and l == Decimal("0.5")):
        return "HALF"
    elif w == Decimal("0.5") and l == Decimal("0.5"):
        return "QUARTER"
    else:
        return f"CUSTOM_{w}x{l}"

def _resolve_material_code(value):
    if not value:
        return None
    material_str = str(value).upper().replace(" ", "")
    if "AISI304" in material_str or material_str == "304": return "AISI304"
    if "AISI316" in material_str or material_str == "316": return "AISI316"
    if "PREGALVANIZ" in material_str or "PREGALV" in material_str: return "PREGALVANIZ"
    if "SDG" in material_str: return "SDG"
    return None

def _is_steel_tank(value):
    if value is None: return False
    tank_type = str(value).strip().lower().replace("ç", "c")
    return tank_type in {"celik", "steel"}

def _resolve_line_category(line, requested_category=None):
    if requested_category:
        return str(requested_category).strip().lower()
    return ZONE_CATEGORY_MAPPING.get(line.zone_type)

def _decompose_side_to_panel_counts(side_length):
    full_count = int(side_length.to_integral_value(rounding=ROUND_FLOOR))
    remainder = side_length - Decimal(full_count)
    half_count = 0
    if remainder >= Decimal("0.5"): half_count = 1
    elif remainder > Decimal("0"): full_count += 1
    return full_count, half_count

def _calculate_surface_panel_plan(width, length, multiplier):
    short_edge = min(width, length)
    long_edge = max(width, length)
    full_rows = int(short_edge.to_integral_value(rounding=ROUND_FLOOR))
    has_half_strip = (short_edge % Decimal("1")) > Decimal("0")
    long_double_count = int((long_edge / Decimal("2")).to_integral_value(rounding=ROUND_FLOOR))
    long_remainder = long_edge % Decimal("2")
    surface_plan = {}
    
    def _add_panel(panel_width_m, panel_length_m, qty):
        if qty <= 0: return
        key = (panel_width_m, panel_length_m)
        surface_plan[key] = surface_plan.get(key, 0) + int(qty)
        
    _add_panel(Decimal("1.0"), Decimal("2.0"), full_rows * long_double_count)
    
    if long_remainder == Decimal("1.5"):
        _add_panel(Decimal("1.0"), Decimal("1.5"), full_rows)
    elif long_remainder == Decimal("1.0"):
        _add_panel(Decimal("1.0"), Decimal("2.0"), full_rows // 2)
        _add_panel(Decimal("1.0"), Decimal("1.0"), full_rows % 2)
    elif long_remainder == Decimal("0.5"):
        _add_panel(Decimal("0.5"), Decimal("2.0"), full_rows // 2)
        _add_panel(Decimal("0.5"), Decimal("1.0"), full_rows % 2)
        
    if has_half_strip:
        _add_panel(Decimal("0.5"), Decimal("2.0"), long_double_count)
        if long_remainder == Decimal("1.5"): _add_panel(Decimal("0.5"), Decimal("1.5"), 1)
        elif long_remainder == Decimal("1.0"): _add_panel(Decimal("0.5"), Decimal("1.0"), 1)
        elif long_remainder == Decimal("0.5"): _add_panel(Decimal("0.5"), Decimal("0.5"), 1)
    
    total_count = sum(surface_plan.values())
    if multiplier > Decimal("1") and total_count > 0:
        adjusted_total = int((Decimal(total_count) * multiplier).to_integral_value(rounding=ROUND_CEILING))
        extra = adjusted_total - total_count
        if extra > 0:
            priority = [
                (Decimal("1.0"), Decimal("2.0")), (Decimal("0.5"), Decimal("2.0")),
                (Decimal("1.0"), Decimal("1.5")), (Decimal("0.5"), Decimal("1.5")),
                (Decimal("1.0"), Decimal("1.0")), (Decimal("0.5"), Decimal("1.0")),
                (Decimal("1.0"), Decimal("0.5")), (Decimal("0.5"), Decimal("0.5")),
            ]
            for key in priority:
                if key in surface_plan:
                    surface_plan[key] += extra
                    break
    return {key: qty for key, qty in surface_plan.items() if qty > 0}

def _calculate_wall_panel_mix(width, length, layer_height, multiplier):
    full_w, half_w = _decompose_side_to_panel_counts(width)
    full_l, half_l = _decompose_side_to_panel_counts(length)
    primary_count = 2 * (full_w + full_l)
    secondary_count = 2 * (half_w + half_l)
    if layer_height <= Decimal("0.5"):
        primary_type = "HORIZONTAL_HALF"
        secondary_type = "QUARTER"
    else:
        primary_type = "FULL"
        secondary_type = "VERTICAL_HALF"

    total_panels = Decimal(primary_count + secondary_count)
    adjusted_total = total_panels
    if multiplier > Decimal("1"):
        adjusted_total = (total_panels * multiplier).to_integral_value(rounding=ROUND_CEILING)
    extra_primary_panels = int(adjusted_total - total_panels)
    primary_count += max(extra_primary_panels, 0)

    return {
        "primary_type": primary_type,
        "secondary_type": secondary_type,
        "primary_qty": Decimal(primary_count),
        "secondary_qty": Decimal(secondary_count),
    }

def _calculate_required_area_m2(line, width, length):
    if line.required_thickness is None: return None
    if line.layer_level is not None:
        perimeter = Decimal("2") * (width + length)
        return perimeter * WALL_MODULE_HEIGHT_M
    return width * length

def _stock_sheet_area_m2(stock):
    if not stock: return None
    if stock.bom_width_mm is None or stock.bom_length_mm is None: return None
    if stock.bom_width_mm <= 0 or stock.bom_length_mm <= 0: return None
    width_m = Decimal(stock.bom_width_mm) / Decimal("1000")
    length_m = Decimal(stock.bom_length_mm) / Decimal("1000")
    return width_m * length_m

def _calculate_required_piece_qty(required_area_m2, sheet_area_m2, multiplier):
    if required_area_m2 is None: return Decimal("1")
    if sheet_area_m2 is None or sheet_area_m2 <= 0: return None
    total_area = required_area_m2 * multiplier
    if total_area <= 0: return Decimal("0")
    return (total_area / sheet_area_m2).to_integral_value(rounding=ROUND_CEILING)

def _get_panel_dimensions_for_type(panel_type):
    if panel_type == "FULL": return Decimal("1.0"), Decimal("1.0")
    if panel_type in {"HALF", "VERTICAL_HALF", "HORIZONTAL_HALF"}: return Decimal("0.5"), Decimal("1.0")
    if panel_type == "QUARTER": return Decimal("0.5"), Decimal("0.5")
    return None, None

def _calculate_gasket_length_for_panels(required_qty, nominal_width_m, nominal_length_m, resolved_stock=None):
    if required_qty is None or required_qty <= 0: return Decimal("0")
    if resolved_stock and resolved_stock.bom_width_mm and resolved_stock.bom_length_mm:
        width_m = Decimal(resolved_stock.bom_width_mm) / Decimal("1000")
        length_m = Decimal(resolved_stock.bom_length_mm) / Decimal("1000")
    else:
        width_m = nominal_width_m
        length_m = nominal_length_m
    perimeter = Decimal("2") * (width_m + length_m)
    return (perimeter * required_qty).quantize(Decimal("0.001"), rounding=ROUND_CEILING)

def _evaluate_stock_and_build_line(stock_obj, required_qty, stock_map, base_line_data, unit="adet", missing_reason=None, extra_line_data=None):
    stock_code = stock_obj.stock_code if stock_obj else None
    available_qty = stock_map.get(stock_code) if stock_code else None
    is_sufficient = None
    shortage = None

    if stock_code and required_qty is not None and available_qty is not None:
        is_sufficient = available_qty >= required_qty
        if not is_sufficient:
            shortage = {
                "stock_code": stock_code,
                "required_qty": float(required_qty),
                "available_qty": float(available_qty),
                "missing_qty": float((required_qty - available_qty).quantize(Decimal("0.001"))),
                "unit": unit,
            }
    else:
        missing_qty_val = float(required_qty.quantize(Decimal("0.001"))) if required_qty is not None else None
        shortage = {
            "stock_code": stock_code,
            "required_qty": missing_qty_val,
            "available_qty": float(available_qty) if available_qty is not None else None,
            "missing_qty": missing_qty_val,
            "unit": unit,
            "reason": missing_reason or "Uygun stok kartı veya bakiye bulunamadı.",
        }

    bom_line = {
        **base_line_data,
        "required_qty": float(required_qty.quantize(Decimal("0.001"))) if required_qty is not None else None,
        "unit": unit,
        "stock_code": stock_code,
        "stock_name": stock_obj.stock_name if stock_obj else None,
        "available_qty": float(available_qty) if available_qty is not None else None,
        "is_sufficient": is_sufficient,
    }

    if extra_line_data:
        bom_line.update(extra_line_data)

    return bom_line, shortage
