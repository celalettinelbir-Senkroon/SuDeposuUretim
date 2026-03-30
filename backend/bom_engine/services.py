from decimal import Decimal, ROUND_CEILING
from django.db.models import Q
from .models import ReferenceBomHeader, ReferenceBomLine, StandardCategory, StockCard
from .constants import (
    MODULE_MM, QUARTER_PANEL_WIDTH_MM, QUARTER_PANEL_LENGTH_MM,
    HALF_PANEL_WIDTH_MM, HALF_PANEL_LENGTH_MM, FULL_PANEL_WIDTH_MM, FULL_PANEL_LENGTH_MM,
    ZONE_CATEGORY_MAPPING
)
from .utils import (
    _to_decimal, _resolve_material_code, _is_steel_tank,
    _resolve_line_category, _calculate_surface_panel_plan,
    _get_panel_type_name, _calculate_gasket_length_for_panels,
    _evaluate_stock_and_build_line, _calculate_wall_panel_mix,
    _get_panel_dimensions_for_type, _calculate_required_area_m2,
    _stock_sheet_area_m2, _calculate_required_piece_qty
)

def _resolve_stock_by_nominal_size(required_thickness, category_code2, nominal_width_m, nominal_length_m, material_code=None):
    if required_thickness is None: return None
    target_width_mm = nominal_width_m * MODULE_MM
    target_length_mm = nominal_length_m * MODULE_MM
    dimension_filter = (
        Q(bom_width_mm=target_width_mm, bom_length_mm=target_length_mm)
        | Q(bom_width_mm=target_length_mm, bom_length_mm=target_width_mm)
    )
    queryset = StockCard.objects.filter(bom_thickness_mm=required_thickness).filter(dimension_filter)
    if category_code2:
        queryset = queryset.filter(bom_category_code2__iexact=category_code2)
    stocks = list(queryset.order_by("is_passive", "stock_code"))
    if stocks: return stocks[0]
    if nominal_width_m == Decimal("0.5") and nominal_length_m == Decimal("0.5"):
        queryset = StockCard.objects.filter(
            bom_thickness_mm=required_thickness, bom_width_mm=QUARTER_PANEL_WIDTH_MM, bom_length_mm=QUARTER_PANEL_LENGTH_MM,
        )
        if category_code2: queryset = queryset.filter(bom_category_code2__iexact=category_code2)
        stocks = list(queryset.order_by("is_passive", "stock_code"))
        if stocks: return stocks[0]
    if nominal_width_m == Decimal("0.5") or nominal_length_m == Decimal("0.5"):
        queryset = StockCard.objects.filter(bom_thickness_mm=required_thickness).filter(
            Q(bom_width_mm=HALF_PANEL_WIDTH_MM, bom_length_mm=HALF_PANEL_LENGTH_MM)
            | Q(bom_width_mm=HALF_PANEL_LENGTH_MM, bom_length_mm=HALF_PANEL_WIDTH_MM)
        )
        if category_code2: queryset = queryset.filter(bom_category_code2__iexact=category_code2)
        stocks = list(queryset.order_by("is_passive", "stock_code"))
        if stocks: return stocks[0]
    return None

def _resolve_stock_by_thickness_and_size(required_thickness, panel_type, material_code=None, category_code2=None):
    if required_thickness is None: return None
    queryset = StockCard.objects.filter(bom_thickness_mm=required_thickness)
    if panel_type == "FULL":
        queryset = queryset.filter(bom_width_mm=FULL_PANEL_WIDTH_MM, bom_length_mm=FULL_PANEL_LENGTH_MM)
    elif panel_type in {"HALF", "VERTICAL_HALF", "HORIZONTAL_HALF"}:
        queryset = queryset.filter(
            Q(bom_width_mm=HALF_PANEL_WIDTH_MM, bom_length_mm=HALF_PANEL_LENGTH_MM) |
            Q(bom_width_mm=HALF_PANEL_LENGTH_MM, bom_length_mm=HALF_PANEL_WIDTH_MM)
        )
    elif panel_type == "QUARTER":
        queryset = queryset.filter(bom_width_mm=QUARTER_PANEL_WIDTH_MM, bom_length_mm=QUARTER_PANEL_LENGTH_MM)
    if category_code2:
        queryset = queryset.filter(bom_category_code2__iexact=category_code2)
    stocks = list(queryset.order_by("is_passive", "stock_code"))
    return stocks[0] if stocks else None

def _resolve_stock_for_line(line, material_code=None, category_code2=None):
    if line.required_thickness is None: return None
    queryset = StockCard.objects.filter(bom_thickness_mm=line.required_thickness)
    if category_code2:
        queryset = queryset.filter(bom_category_code2__iexact=category_code2)
    stocks = list(queryset.order_by("is_passive", "stock_code"))
    return stocks[0] if stocks else None

def _resolve_manhole_stock(required_thickness=None, material_code=None):
    queryset = StockCard.objects.all()
    if required_thickness is not None:
        queryset = queryset.filter(bom_thickness_mm=required_thickness)
    if material_code:
        queryset = queryset.filter(
            Q(bom_category_code1__icontains=material_code) | Q(bom_category_code2__icontains=material_code) |
            Q(bom_category_code3__icontains=material_code) | Q(bom_category_code4__icontains=material_code)
        )
    cover_category = ZONE_CATEGORY_MAPPING.get("COVER")
    queryset = queryset.filter(
        Q(bom_category_code2__iexact=cover_category) | Q(stock_name__icontains="manhole") | Q(stock_name__icontains="kapak")
    )
    stocks = list(queryset.order_by("is_passive", "stock_code"))
    return stocks[0] if stocks else None

def _resolve_conta_stock(zone_type, material_code=None):
    queryset = StockCard.objects.filter(
        Q(bom_category_code2__icontains="conta") | Q(stock_name__icontains="conta")
    )
    # if material_code:
    #     queryset = queryset.filter(
    #         Q(bom_category_code1__icontains=material_code) | Q(bom_category_code2__icontains=material_code) |
    #         Q(bom_category_code3__icontains=material_code) | Q(bom_category_code4__icontains=material_code)
    #     )
    if zone_type == "BASE":
        queryset = queryset.filter(stock_name__icontains="Taban Contası")
    if zone_type == "ROOF":
        queryset = queryset.filter(stock_name__icontains="Tavan Contası")
    if zone_type == "WALL":
        queryset = queryset.filter(stock_name__icontains="Modül Contası")
    if zone_type == "EXTERNAL_ANGLE":
        queryset = queryset.filter(stock_name__icontains="Köşebent Contası")
    return queryset.order_by("is_passive", "stock_code").first()

def _append_conta_bom_line(bom_lines, shortages, stock_map, zone_type, required_qty, material_code):
    if required_qty is None or required_qty <= 0: return
    stock_obj = _resolve_conta_stock(zone_type, material_code=material_code)
    stock_code = stock_obj.stock_code if stock_obj else None
    available_qty = stock_map.get(stock_code) if stock_code else None
    is_sufficient = None
    if stock_code and available_qty is not None:
        is_sufficient = available_qty >= required_qty
        if not is_sufficient:
            shortages.append({
                "stock_code": stock_code, "required_qty": float(required_qty),
                "available_qty": float(available_qty), "missing_qty": float((required_qty - available_qty).quantize(Decimal("0.001"))),
                "unit": "metre",
            })
    else:
        shortages.append({
            "stock_code": stock_code, "required_qty": float(required_qty),
            "available_qty": float(available_qty) if available_qty is not None else None,
            "missing_qty": float(required_qty), "unit": "metre",
            "reason": f"{zone_type} icin conta stok karsiligi bulunamadi.",
        })
    bom_lines.append({
        "zone_type": f"{zone_type}_CONTA", "layer_level": None, "required_thickness": None, "stock_category": "conta",
        "required_qty": float(required_qty), "unit": "metre", "stock_code": stock_code,
        "stock_name": stock_obj.stock_name if stock_obj else None,
        "available_qty": float(available_qty) if available_qty is not None else None,
        "is_sufficient": is_sufficient,
    })

def _add_ladders_to_bom(tank_height_m, bom_lines, inner_ladder_type="Çelik"):
    tank_height_mm = tank_height_m * 1000
    inner_ladder_cat4 = "Çelik Yarımamul" if inner_ladder_type == "Çelik" else "Grp Yarımamul"
    selected_outer_ladder = StockCard.objects.filter(
        bom_category_code3='Merdiven', bom_category_code4='Ortak Yarımamul', bom_length_mm__gte=tank_height_mm
    ).order_by('bom_length_mm').first()
    selected_inner_ladder = StockCard.objects.filter(
        bom_category_code3='Merdiven', bom_category_code4=inner_ladder_cat4, bom_length_mm__lte=tank_height_mm, bom_length_mm__gt=0
    ).order_by('-bom_length_mm').first()
    items_to_add = []
    if selected_outer_ladder: items_to_add.append(selected_outer_ladder)
    if selected_inner_ladder: items_to_add.append(selected_inner_ladder)
    for item in items_to_add:
        bom_lines.append({
            "zone_type": "ACCESSORY", "layer_level": None, "required_thickness": None,
            "stock_category": item.bom_category_code2, "required_qty": float(1.0),
            "unit": item.unit_name or "Adet", "stock_code": item.stock_code,
            "stock_name": item.stock_name, "available_qty": None, "is_sufficient": None,
        })
    return bom_lines

def build_empty_payload(payload):
    payload.update({
        "matched_header": None, "bom_lines": [],
        "warehouse_check": { "is_available": False, "shortages": [] },
    })

def process_base_roof(line, width, length, multiplier, material_code, line_category, stock_map, base_data, bom_lines, shortages, conta_totals):
    surface_plan = _calculate_surface_panel_plan(width=width, length=length, multiplier=multiplier)
    conta_length = Decimal("0")
    for (panel_width_m, panel_length_m), panel_count in surface_plan.items():
        required_qty = Decimal(panel_count)
        if required_qty <= 0: continue
        resolved_stock = _resolve_stock_by_nominal_size(
            required_thickness=line.required_thickness, category_code2=line_category,
            nominal_width_m=panel_width_m, nominal_length_m=panel_length_m, material_code=material_code,
        )
        panel_conta = _calculate_gasket_length_for_panels(required_qty, panel_width_m, panel_length_m, resolved_stock=resolved_stock)
        conta_length += panel_conta
        panel_type_name = _get_panel_type_name(panel_width_m, panel_length_m)
        extra_data = { "panel_type": f"{panel_width_m}x{panel_length_m}", "panel_type_name": panel_type_name }
        reason = f"{line.zone_type} icin {panel_width_m}x{panel_length_m}m ({panel_type_name}) panel stok karsiligi bulunamadi."
        b_line, s_line = _evaluate_stock_and_build_line(
            resolved_stock, required_qty, stock_map, base_data, missing_reason=reason, extra_line_data=extra_data,
        )
        bom_lines.append(b_line)
        if s_line: shortages.append(s_line)
    if conta_length > 0:
        conta_totals[line.zone_type] = conta_totals.get(line.zone_type, Decimal("0")) + conta_length

def process_wall(line, width, length, multiplier, material_code, line_category, layer_height_map, first_wall_layer, stock_map, base_data, bom_lines, shortages, conta_totals):
    layer_height = layer_height_map.get(line.layer_level, Decimal("1"))
    panel_mix = _calculate_wall_panel_mix(width=width, length=length, layer_height=layer_height, multiplier=multiplier)
    is_first_wall_layer = first_wall_layer is not None and line.layer_level == first_wall_layer
    if is_first_wall_layer:
        if panel_mix["primary_qty"] > 0: panel_mix["primary_qty"] -= Decimal("1")
        elif panel_mix["secondary_qty"] > 0: panel_mix["secondary_qty"] -= Decimal("1")
    wall_parts = [
        (panel_mix["primary_type"], panel_mix["primary_qty"]),
        (panel_mix["secondary_type"], panel_mix["secondary_qty"]),
    ]
    conta_length = Decimal("0")
    for panel_type, required_qty in wall_parts:
        if required_qty <= 0: continue
        resolved_stock = _resolve_stock_by_thickness_and_size(
            required_thickness=line.required_thickness, panel_type=panel_type,
            material_code=material_code, category_code2=line_category,
        )
        nominal_width_m, nominal_length_m = _get_panel_dimensions_for_type(panel_type)
        panel_conta = _calculate_gasket_length_for_panels(
            required_qty, nominal_width_m, nominal_length_m, resolved_stock=resolved_stock,
        )
        conta_length += panel_conta
        extra_data = { "panel_type": panel_type, "manhole_deducted": is_first_wall_layer }
        reason = f"{panel_type} panel icin uygun stok karti bulunamadi."
        b_line, s_line = _evaluate_stock_and_build_line(
            resolved_stock, required_qty, stock_map, base_data, missing_reason=reason, extra_line_data=extra_data,
        )
        bom_lines.append(b_line)
        if s_line: shortages.append(s_line)
    if conta_length > 0:
        conta_totals["WALL"] = conta_totals.get("WALL", Decimal("0")) + conta_length

def process_external_angle(line, height, material_code, line_category, stock_map, base_data, bom_lines, shortages):
    required_qty = Decimal("4")
    resolved_stock = _resolve_stock_by_nominal_size(
        required_thickness=line.required_thickness, category_code2=line_category,
        nominal_width_m=Decimal(), nominal_length_m=height, material_code=material_code
    )
    if not resolved_stock:
        resolved_stock = _resolve_stock_for_line(line, material_code=material_code, category_code2=line_category)
    reason = f"Dış Köşebent (Kalınlık: {line.required_thickness}mm, Boy: {height}m) için uygun stok kartı bulunamadı."
    b_line, s_line = _evaluate_stock_and_build_line(resolved_stock, required_qty, stock_map, base_data, missing_reason=reason)
    bom_lines.append(b_line)
    if s_line: shortages.append(s_line)

def process_internal_tie(line, height, multiplier, material_code, line_category, stock_map, base_data, bom_lines, shortages):
    WALL_MODULE_HEIGHT_M = Decimal("1.08")
    required_qty = (height / WALL_MODULE_HEIGHT_M).to_integral_value(rounding=ROUND_CEILING) * multiplier
    resolved_stock = _resolve_stock_for_line(line, material_code=material_code, category_code2=line_category)
    reason = "İç Gergi icin uygun stok karti bulunamadi."
    b_line, s_line = _evaluate_stock_and_build_line(resolved_stock, required_qty, stock_map, base_data, missing_reason=reason)
    bom_lines.append(b_line)
    if s_line: shortages.append(s_line)

def process_fallback_and_accessories(line, width, length, multiplier, material_code, line_category, stock_map, base_data, bom_lines, shortages):
    resolved_stock = _resolve_stock_for_line(line, material_code=material_code, category_code2=line_category)
    if line.zone_type in {"COVER", "ACCESSORY"}:
        required_area_m2 = None
        sheet_area_m2 = None
        base_required_qty = Decimal("1")
        required_qty = Decimal("1")
    else:
        required_area_m2 = _calculate_required_area_m2(line, width, length)
        sheet_area_m2 = _stock_sheet_area_m2(resolved_stock)
        required_qty = _calculate_required_piece_qty(required_area_m2=required_area_m2, sheet_area_m2=sheet_area_m2, multiplier=multiplier)
        base_required_qty = required_area_m2.quantize(Decimal("0.001")) if required_area_m2 is not None else Decimal("1")
    extra_data = {
        "base_required_qty": float(base_required_qty.quantize(Decimal("0.001"))),
        "sheet_area_m2": float(sheet_area_m2.quantize(Decimal("0.001"))) if sheet_area_m2 is not None else None,
    }
    reason = "Bu satir icin uygun stok karti bulunamadi." if not resolved_stock else "Stok kartinda panel ebatlari eksik oldugu icin adet hesabi yapilamadi."
    b_line, s_line = _evaluate_stock_and_build_line(resolved_stock, required_qty, stock_map, base_data, missing_reason=reason, extra_line_data=extra_data)
    bom_lines.append(b_line)
    if s_line: shortages.append(s_line)


def calculate_tank(width, length, height, standard_raw):
    volume_m3 = width * length * height
    capacity_ton = volume_m3

    standard = StandardCategory.objects.filter(name__iexact=str(standard_raw).strip()).only("id", "name").first()

    response_payload = {
        "inputs": {
            "en": float(width), "boy": float(length), "yukseklik": float(height), "standart": str(standard_raw).strip(),
        },
        "calculation": {
            "volume_m3": float(volume_m3.quantize(Decimal("0.001"))), "capacity_ton": float(capacity_ton.quantize(Decimal("0.001"))),
        },
        "standard_found": bool(standard),
    }

    if not standard:
        response_payload.update({"matched_header": None, "bom_lines": []})
        return response_payload

    header = ReferenceBomHeader.objects.filter(
        category=standard, min_tonnage__lte=capacity_ton, max_tonnage__gte=capacity_ton,
    ).select_related("category").order_by("min_tonnage").first()

    response_payload["matched_standard"] = {"id": standard.id, "name": standard.name}

    if not header:
        response_payload.update({"matched_header": None, "bom_lines": []})
        return response_payload

    lines_qs = ReferenceBomLine.objects.filter(bom_header=header).order_by("total_module_height", "zone_type", "layer_level")
    unique_heights = sorted({line.total_module_height for line in lines_qs})

    if unique_heights:
        selected_height = min(unique_heights, key=lambda h: abs(h - height))
        selected_lines = [line for line in lines_qs if line.total_module_height == selected_height]
    else:
        selected_height = None
        selected_lines = []

    response_payload["matched_header"] = {
        "id": header.id, "material_type": header.material_type,
        "tonnage_range": {"min": header.min_tonnage, "max": header.max_tonnage},
        "selected_module_height": float(selected_height) if selected_height is not None else None,
    }
    response_payload["bom_lines"] = [
        {
            "zone_type": line.zone_type,
            "layer_level": float(line.layer_level) if line.layer_level is not None else None,
            "required_thickness": float(line.required_thickness) if line.required_thickness is not None else None,
            "stock_code": line.stock_card.stock_code if line.stock_card else None,
        }
        for line in selected_lines
    ]
    return response_payload


def calculate_warehouse_recipe(width, length, height, standard_raw, material_raw, tank_type_raw, warehouse_stocks):
    volume_m3 = width * length * height
    capacity_ton = volume_m3
    requirement_multiplier = Decimal("1.08") if _is_steel_tank(tank_type_raw) else Decimal("1")
    material_code = _resolve_material_code(material_raw or "")

    standard = StandardCategory.objects.filter(name__iexact=str(standard_raw).strip()).only("id", "name").first()

    payload = {
        "inputs": {
            "en": float(width), "boy": float(length), "yukseklik": float(height), "standart": str(standard_raw).strip(),
            "malzeme": str(material_raw).strip() if material_raw else None,
            "depo_tipi": str(tank_type_raw).strip() if tank_type_raw else None,
        },
        "calculation": {
            "volume_m3": float(volume_m3.quantize(Decimal("0.001"))), "capacity_ton": float(capacity_ton.quantize(Decimal("0.001"))),
            "requirement_multiplier": float(requirement_multiplier),
        },
        "standard_found": bool(standard),
    }

    if not standard:
        build_empty_payload(payload)
        return payload

    headers = ReferenceBomHeader.objects.filter(category=standard, min_tonnage__lte=capacity_ton, max_tonnage__gte=capacity_ton).order_by("min_tonnage")
    if material_raw:
        headers = headers.filter(material_type__icontains=str(material_raw).strip())
    header = headers.select_related("category").first()

    payload["matched_standard"] = {"id": standard.id, "name": standard.name}

    if not header:
        build_empty_payload(payload)
        return payload

    lines_qs = ReferenceBomLine.objects.filter(bom_header=header).select_related("stock_card").order_by("total_module_height", "zone_type", "layer_level")
    unique_heights = sorted({line.total_module_height for line in lines_qs})

    if unique_heights:
        selected_height = min(unique_heights, key=lambda h: abs(h - height))
        selected_lines = [line for line in lines_qs if line.total_module_height == selected_height]
    else:
        selected_height = None
        selected_lines = []

    stock_map = {}
    if isinstance(warehouse_stocks, list):
        for item in warehouse_stocks:
            if not isinstance(item, dict): continue
            stock_code = item.get("stock_code")
            qty = _to_decimal(item.get("qty", item.get("quantity")))
            if stock_code and qty is not None:
                stock_map[str(stock_code)] = qty

    wall_layer_levels = sorted({line.layer_level for line in selected_lines if line.zone_type == "WALL" and line.layer_level is not None})
    first_wall_layer = wall_layer_levels[0] if wall_layer_levels else None
    
    layer_height_map = {}
    previous_level = Decimal("0")
    for level in wall_layer_levels:
        layer_height = level - previous_level
        if layer_height <= 0: layer_height = Decimal("0.5")
        layer_height_map[level] = layer_height
        previous_level = level

    shortages = []
    bom_lines = []
    conta_totals = {}

    for line in selected_lines:
        line_category = _resolve_line_category(line)
        base_line_data = {
            "zone_type": line.zone_type, "layer_level": float(line.layer_level) if line.layer_level is not None else None,
            "required_thickness": float(line.required_thickness) if line.required_thickness is not None else None,
            "stock_category": line_category,
        }

        if line.zone_type in {"BASE", "ROOF"} and line.required_thickness is not None:
            process_base_roof(line, width, length, requirement_multiplier, material_code, line_category, stock_map, base_line_data, bom_lines, shortages, conta_totals)
        elif line.zone_type == "WALL" and line.required_thickness is not None:
            process_wall(line, width, length, requirement_multiplier, material_code, line_category, layer_height_map, first_wall_layer, stock_map, base_line_data, bom_lines, shortages, conta_totals)
        elif line.zone_type == "EXTERNAL_ANGLE" and line.required_thickness is not None:
            process_external_angle(line, height, material_code, line_category, stock_map, base_line_data, bom_lines, shortages)
        elif line.zone_type == "INTERNAL_TIE" and line.required_thickness is not None:
            process_internal_tie(line, height, requirement_multiplier, material_code, line_category, stock_map, base_line_data, bom_lines, shortages)
        else:
            process_fallback_and_accessories(line, width, length, requirement_multiplier, material_code, line_category, stock_map, base_line_data, bom_lines, shortages)

    w_plus_l = width + length
    scaled_boundary = Decimal("2") * w_plus_l * requirement_multiplier

    base_perim_sum = conta_totals.get("BASE", Decimal("0"))
    if base_perim_sum > 0:
        taban_conta = (base_perim_sum + scaled_boundary) / Decimal("2")
        _append_conta_bom_line(bom_lines, shortages, stock_map, "BASE", taban_conta, material_code)

    roof_perim_sum = conta_totals.get("ROOF", Decimal("0"))
    if roof_perim_sum > 0:
        tavan_conta = (roof_perim_sum + scaled_boundary) / Decimal("2")
        _append_conta_bom_line(bom_lines, shortages, stock_map, "ROOF", tavan_conta, material_code)

    wall_perim_sum = conta_totals.get("WALL", Decimal("0"))
    if wall_perim_sum > 0:
        kosebent_conta = Decimal("4") * height
        total_wall_joints = (wall_perim_sum - Decimal("2") * scaled_boundary) / Decimal("2")
        modul_conta = total_wall_joints - kosebent_conta
        if modul_conta < Decimal("0"):
            modul_conta = Decimal("0")

        _append_conta_bom_line(bom_lines, shortages, stock_map, "WALL", modul_conta, material_code)
        if kosebent_conta > 0:
            _append_conta_bom_line(bom_lines, shortages, stock_map, "EXTERNAL_ANGLE", kosebent_conta, material_code)

    bom_lines = _add_ladders_to_bom(tank_height_m=float(height), bom_lines=bom_lines, inner_ladder_type="Çelik")

    payload["matched_header"] = {
        "id": header.id, "material_type": header.material_type,
        "tonnage_range": {"min": header.min_tonnage, "max": header.max_tonnage},
        "selected_module_height": float(selected_height) if selected_height is not None else None,
    }
    payload["bom_lines"] = bom_lines
    payload["warehouse_check"] = {"is_available": len(shortages) == 0, "shortages": shortages}

    return payload
