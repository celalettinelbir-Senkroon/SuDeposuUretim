from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_FLOOR

from django.db.models import Q

from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .models import ReferenceBomHeader, ReferenceBomLine, StandardCategory, StockCard


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


def _to_decimal(value):
	try:
		return Decimal(str(value))
	except (InvalidOperation, ValueError, TypeError):
		return None


def _get_panel_type_name(panel_width_m, panel_length_m):
	"""Nominal dimensions'tan panel türü adı döndür"""
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
	if "AISI304" in material_str or material_str == "304":
		return "AISI304"
	if "AISI316" in material_str or material_str == "316":
		return "AISI316"
	if "PREGALVANIZ" in material_str or "PREGALV" in material_str:
		return "PREGALVANIZ"
	if "SDG" in material_str:
		return "SDG"

	return None


def _is_steel_tank(value):
	if value is None:
		return False

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

	if remainder >= Decimal("0.5"):
		half_count = 1
	elif remainder > Decimal("0"):
		# 0.5 olmayan artık için eksik kalmaması adına bir tam panel eklenir.
		full_count += 1

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
		if qty <= 0:
			return
		key = (panel_width_m, panel_length_m)
		surface_plan[key] = surface_plan.get(key, 0) + int(qty)

	# Bolum 2: Ana govde (1m satirlar)
	_add_panel(Decimal("1.0"), Decimal("2.0"), full_rows * long_double_count)

	if long_remainder == Decimal("1.5"):
		_add_panel(Decimal("1.0"), Decimal("1.5"), full_rows)
	elif long_remainder == Decimal("1.0"):
		_add_panel(Decimal("1.0"), Decimal("2.0"), full_rows // 2)
		_add_panel(Decimal("1.0"), Decimal("1.0"), full_rows % 2)
	elif long_remainder == Decimal("0.5"):
		_add_panel(Decimal("0.5"), Decimal("2.0"), full_rows // 2)
		_add_panel(Decimal("0.5"), Decimal("1.0"), full_rows % 2)

	# Bolum 3: Ince serit (0.5m satir)
	if has_half_strip:
		_add_panel(Decimal("0.5"), Decimal("2.0"), long_double_count)

		if long_remainder == Decimal("1.5"):
			_add_panel(Decimal("0.5"), Decimal("1.5"), 1)
		elif long_remainder == Decimal("1.0"):
			_add_panel(Decimal("0.5"), Decimal("1.0"), 1)
		elif long_remainder == Decimal("0.5"):
			_add_panel(Decimal("0.5"), Decimal("0.5"), 1)

	total_count = sum(surface_plan.values())
	if multiplier > Decimal("1") and total_count > 0:
		adjusted_total = int((Decimal(total_count) * multiplier).to_integral_value(rounding=ROUND_CEILING))
		extra = adjusted_total - total_count
		if extra > 0:
			priority = [
				(Decimal("1.0"), Decimal("2.0")),
				(Decimal("0.5"), Decimal("2.0")),
				(Decimal("1.0"), Decimal("1.5")),
				(Decimal("0.5"), Decimal("1.5")),
				(Decimal("1.0"), Decimal("1.0")),
				(Decimal("0.5"), Decimal("1.0")),
				(Decimal("1.0"), Decimal("0.5")),
				(Decimal("0.5"), Decimal("0.5")),
			]
			for key in priority:
				if key in surface_plan:
					surface_plan[key] += extra
					break

	# Bolum 4: Sadece adet > 0 olan tipleri dondur.
	return {key: qty for key, qty in surface_plan.items() if qty > 0}


def _resolve_stock_by_nominal_size(required_thickness, category_code2, nominal_width_m, nominal_length_m, material_code=None):
	if required_thickness is None:
		return None

	target_width_mm = nominal_width_m * MODULE_MM
	target_length_mm = nominal_length_m * MODULE_MM

	# Çift yönlü eşleştirme: (w, l) veya (l, w)
	dimension_filter = (
		Q(bom_width_mm=target_width_mm, bom_length_mm=target_length_mm)
		| Q(bom_width_mm=target_length_mm, bom_length_mm=target_width_mm)
	)

	queryset = StockCard.objects.filter(
		bom_thickness_mm=required_thickness,
	).filter(dimension_filter)

	if category_code2:
		queryset = queryset.filter(bom_category_code2__iexact=category_code2)

	stocks = list(queryset.order_by("is_passive", "stock_code"))
	if stocks:
		return stocks[0]

	# Fallback temel panel türlerine göre arama (iki tarafı da yarIMlı durum için)
	if nominal_width_m == Decimal("0.5") and nominal_length_m == Decimal("0.5"):
		# QUARTER panel olarak ara
		queryset = StockCard.objects.filter(
			bom_thickness_mm=required_thickness,
			bom_width_mm=QUARTER_PANEL_WIDTH_MM,
			bom_length_mm=QUARTER_PANEL_LENGTH_MM,
		)
		if category_code2:
			queryset = queryset.filter(bom_category_code2__iexact=category_code2)
		stocks = list(queryset.order_by("is_passive", "stock_code"))
		if stocks:
			return stocks[0]

	# Eğer hala bulunamadığı durum, en küçükten başlayarak alternatif panelleri ara
	if nominal_width_m == Decimal("0.5") or nominal_length_m == Decimal("0.5"):
		# 0.5 boyutlu panelleri ara (HALF panellerini denetle)
		queryset = StockCard.objects.filter(
			bom_thickness_mm=required_thickness,
		).filter(
			Q(bom_width_mm=HALF_PANEL_WIDTH_MM, bom_length_mm=HALF_PANEL_LENGTH_MM)
			| Q(bom_width_mm=HALF_PANEL_LENGTH_MM, bom_length_mm=HALF_PANEL_WIDTH_MM)
		)
		if category_code2:
			queryset = queryset.filter(bom_category_code2__iexact=category_code2)
		stocks = list(queryset.order_by("is_passive", "stock_code"))
		if stocks:
			return stocks[0]

	return None


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


def _resolve_stock_by_thickness_and_size(required_thickness, panel_type, material_code=None, category_code2=None):
	if required_thickness is None:
		return None

	queryset = StockCard.objects.filter(
		bom_thickness_mm=required_thickness,
	)

	if panel_type == "FULL":
		queryset = queryset.filter(
			bom_width_mm=FULL_PANEL_WIDTH_MM,
			bom_length_mm=FULL_PANEL_LENGTH_MM,
		)
	elif panel_type in {"HALF", "VERTICAL_HALF", "HORIZONTAL_HALF"}:
		queryset = queryset.filter(
			Q(bom_width_mm=HALF_PANEL_WIDTH_MM, bom_length_mm=HALF_PANEL_LENGTH_MM)
			| Q(bom_width_mm=HALF_PANEL_LENGTH_MM, bom_length_mm=HALF_PANEL_WIDTH_MM)
		)
	elif panel_type == "QUARTER":
		queryset = queryset.filter(
			bom_width_mm=QUARTER_PANEL_WIDTH_MM,
			bom_length_mm=QUARTER_PANEL_LENGTH_MM,
		)

	# if material_code:
	# 	queryset = queryset.filter(
	# 		Q(bom_category_code1__icontains=material_code)
	# 		| Q(bom_category_code2__icontains=material_code)
	# 		| Q(bom_category_code3__icontains=material_code)
	# 		| Q(bom_category_code4__icontains=material_code)
	# 	)

	if category_code2:
		queryset = queryset.filter(bom_category_code2__iexact=category_code2)

	


	stocks = list(queryset.order_by("is_passive", "stock_code"))
	return stocks[0] if stocks else None


def _resolve_stock_for_line(line, material_code=None, category_code2=None):
	if line.required_thickness is None:
		return None

	queryset = StockCard.objects.filter(bom_thickness_mm=line.required_thickness)

	# if material_code:
	# 	queryset = queryset.filter(
	# 		Q(bom_category_code1__icontains=material_code)
	# 		| Q(bom_category_code2__icontains=material_code)
	# 		| Q(bom_category_code3__icontains=material_code)
	# 		| Q(bom_category_code4__icontains=material_code)
	# 	)

	
 
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
			Q(bom_category_code1__icontains=material_code)
			| Q(bom_category_code2__icontains=material_code)
			| Q(bom_category_code3__icontains=material_code)
			| Q(bom_category_code4__icontains=material_code)
		)

	cover_category = ZONE_CATEGORY_MAPPING.get("COVER")
	queryset = queryset.filter(
		Q(bom_category_code2__iexact=cover_category)
		| Q(stock_name__icontains="manhole")
		| Q(stock_name__icontains="kapak")
	)

	stocks = list(queryset.order_by("is_passive", "stock_code"))
	return stocks[0] if stocks else None


def _calculate_required_area_m2(line, width, length):
	if line.required_thickness is None:
		return None

	if line.layer_level is not None:
		perimeter = Decimal("2") * (width + length)
		return perimeter * WALL_MODULE_HEIGHT_M

	return width * length


def _stock_sheet_area_m2(stock):
	if not stock:
		return None

	if stock.bom_width_mm is None or stock.bom_length_mm is None:
		return None

	if stock.bom_width_mm <= 0 or stock.bom_length_mm <= 0:
		return None

	width_m = Decimal(stock.bom_width_mm) / Decimal("1000")
	length_m = Decimal(stock.bom_length_mm) / Decimal("1000")
	return width_m * length_m


def _calculate_required_piece_qty(required_area_m2, sheet_area_m2, multiplier):
	if required_area_m2 is None:
		return Decimal("1")

	if sheet_area_m2 is None or sheet_area_m2 <= 0:
		return None

	total_area = required_area_m2 * multiplier
	if total_area <= 0:
		return Decimal("0")

	return (total_area / sheet_area_m2).to_integral_value(rounding=ROUND_CEILING)


class TankCalculationView(APIView):
	permission_classes = [AllowAny]

	def post(self, request):
		width_raw = request.data.get("en", request.data.get("width"))
		length_raw = request.data.get("boy", request.data.get("length"))
		height_raw = request.data.get("yukseklik", request.data.get("height"))
		standard_raw = request.data.get("standart", request.data.get("standard"))

		if width_raw is None or length_raw is None or height_raw is None or not standard_raw:
			return JsonResponse(
				{
					"detail": "'en', 'boy', 'yukseklik' ve 'standart' alanlari zorunludur."
				},
				status=400,
			)

		try:
			width = Decimal(str(width_raw))
			length = Decimal(str(length_raw))
			height = Decimal(str(height_raw))
		except (InvalidOperation, ValueError, TypeError):
			return JsonResponse(
				{
					"detail": "'en', 'boy' ve 'yukseklik' sayisal bir deger olmali."
				},
				status=400,
			)

		if width <= 0 or length <= 0 or height <= 0:
			return JsonResponse(
				{
					"detail": "'en', 'boy' ve 'yukseklik' sifirdan buyuk olmali."
				},
				status=400,
			)

		volume_m3 = width * length * height
		capacity_ton = volume_m3

		standard = (
			StandardCategory.objects.filter(name__iexact=str(standard_raw).strip())
			.only("id", "name")
			.first()
		)

		response_payload = {
			"inputs": {
				"en": float(width),
				"boy": float(length),
				"yukseklik": float(height),
				"standart": str(standard_raw).strip(),
			},
			"calculation": {
				"volume_m3": float(volume_m3.quantize(Decimal("0.001"))),
				"capacity_ton": float(capacity_ton.quantize(Decimal("0.001"))),
			},
			"standard_found": bool(standard),
		}

		if not standard:
			response_payload["matched_header"] = None
			response_payload["bom_lines"] = []
			return JsonResponse(response_payload, status=200)

		header = (
			ReferenceBomHeader.objects.filter(
				category=standard,
				min_tonnage__lte=capacity_ton,
				max_tonnage__gte=capacity_ton,
			)
			.select_related("category")
			.order_by("min_tonnage")
			.first()
		)

		response_payload["matched_standard"] = {
			"id": standard.id,
			"name": standard.name,
		}

		if not header:
			response_payload["matched_header"] = None
			response_payload["bom_lines"] = []
			return JsonResponse(response_payload, status=200)

		lines_qs = ReferenceBomLine.objects.filter(bom_header=header).order_by(
			"total_module_height", "zone_type", "layer_level"
		)
		unique_heights = sorted({line.total_module_height for line in lines_qs})

		if unique_heights:
			selected_height = min(unique_heights, key=lambda h: abs(h - height))
			selected_lines = [line for line in lines_qs if line.total_module_height == selected_height]
		else:
			selected_height = None
			selected_lines = []

		response_payload["matched_header"] = {
			"id": header.id,
			"material_type": header.material_type,
			"tonnage_range": {
				"min": header.min_tonnage,
				"max": header.max_tonnage,
			},
			"selected_module_height": float(selected_height) if selected_height is not None else None,
		}
		response_payload["bom_lines"] = [
			{
				"zone_type": line.zone_type,
				"layer_level": float(line.layer_level) if line.layer_level is not None else None,
				"required_thickness": (
					float(line.required_thickness)
					if line.required_thickness is not None
					else None
				),
				"stock_code": line.stock_card.stock_code if line.stock_card else None,
			}
			for line in selected_lines
		]

		return JsonResponse(response_payload, status=200)


class WarehouseRecipeCalculationView(APIView):
	permission_classes = [AllowAny]

	def post(self, request):
		width_raw = request.data.get("en", request.data.get("width"))
		length_raw = request.data.get("boy", request.data.get("length"))
		height_raw = request.data.get("yukseklik", request.data.get("height"))
		standard_raw = request.data.get("standart", request.data.get("standard"))
		material_raw = request.data.get("malzeme", request.data.get("material_type"))
		tank_type_raw = request.data.get("depo_tipi", request.data.get("tank_type"))
		warehouse_stocks = request.data.get("depo_stoklari", request.data.get("warehouse_stocks", []))

		if width_raw is None or length_raw is None or height_raw is None or not standard_raw:
			return JsonResponse(
				{
					"detail": "'en', 'boy', 'yukseklik' ve 'standart' alanlari zorunludur."
				},
				status=400,
			)

		width = _to_decimal(width_raw)
		length = _to_decimal(length_raw)
		height = _to_decimal(height_raw)

		if width is None or length is None or height is None:
			return JsonResponse(
				{"detail": "'en', 'boy' ve 'yukseklik' sayisal bir deger olmali."},
				status=400,
			)

		if width <= 0 or length <= 0 or height <= 0:
			return JsonResponse(
				{"detail": "'en', 'boy' ve 'yukseklik' sifirdan buyuk olmali."},
				status=400,
			)

		volume_m3 = width * length * height
		capacity_ton = volume_m3
		requirement_multiplier = Decimal("1.08") if _is_steel_tank(tank_type_raw) else Decimal("1")

		standard = (
			StandardCategory.objects.filter(name__iexact=str(standard_raw).strip())
			.only("id", "name")
			.first()
		)

		payload = {
			"inputs": {
				"en": float(width),
				"boy": float(length),
				"yukseklik": float(height),
				"standart": str(standard_raw).strip(),
				"malzeme": str(material_raw).strip() if material_raw else None,
				"depo_tipi": str(tank_type_raw).strip() if tank_type_raw else None,
			},
			"calculation": {
				"volume_m3": float(volume_m3.quantize(Decimal("0.001"))),
				"capacity_ton": float(capacity_ton.quantize(Decimal("0.001"))),
				"requirement_multiplier": float(requirement_multiplier),
			},
			"standard_found": bool(standard),
		}

		if not standard:
			payload.update(
				{
					"matched_header": None,
					"bom_lines": [],
					"warehouse_check": {
						"is_available": False,
						"shortages": [],
					},
				}
			)
			return JsonResponse(payload, status=200)

		headers = ReferenceBomHeader.objects.filter(
			category=standard,
			min_tonnage__lte=capacity_ton,
			max_tonnage__gte=capacity_ton,
		).order_by("min_tonnage")

		if material_raw:
			headers = headers.filter(material_type__icontains=str(material_raw).strip())

		header = headers.select_related("category").first()

		payload["matched_standard"] = {
			"id": standard.id,
			"name": standard.name,
		}

		if not header:
			payload.update(
				{
					"matched_header": None,
					"bom_lines": [],
					"warehouse_check": {
						"is_available": False,
						"shortages": [],
					},
				}
			)
			return JsonResponse(payload, status=200)

		lines_qs = (
			ReferenceBomLine.objects.filter(bom_header=header)
			.select_related("stock_card")
			.order_by("total_module_height", "zone_type", "layer_level")
		)
		unique_heights = sorted({line.total_module_height for line in lines_qs})

		if unique_heights:
			selected_height = min(unique_heights, key=lambda h: abs(h - height))
			selected_lines = [line for line in lines_qs if line.total_module_height == selected_height]
		else:
			selected_height = None
			selected_lines = []

		material_code = _resolve_material_code(material_raw or header.material_type)

		stock_map = {}
		if isinstance(warehouse_stocks, list):
			for item in warehouse_stocks:
				if not isinstance(item, dict):
					continue
				stock_code = item.get("stock_code")
				qty = _to_decimal(item.get("qty", item.get("quantity")))
				if stock_code and qty is not None:
					stock_map[str(stock_code)] = qty

		shortages = []
		bom_lines = []
		wall_layer_levels = sorted(
			{
				line.layer_level
				for line in selected_lines
				if line.zone_type == "WALL" and line.layer_level is not None
			}
		)
		first_wall_layer = wall_layer_levels[0] if wall_layer_levels else None
		layer_height_map = {}
		previous_level = Decimal("0")
		for level in wall_layer_levels:
			layer_height = level - previous_level
			if layer_height <= 0:
				layer_height = Decimal("0.5")
			layer_height_map[level] = layer_height
			previous_level = level

		for line in selected_lines:
			line_category = _resolve_line_category(line)

			if line.zone_type in {"BASE", "ROOF"} and line.required_thickness is not None:
				surface_plan = _calculate_surface_panel_plan(
					width=width,
					length=length,
					multiplier=requirement_multiplier,
				)

				for (panel_width_m, panel_length_m), panel_count in surface_plan.items():
					required_qty = Decimal(panel_count)
					if required_qty <= 0:
						continue

					resolved_stock = _resolve_stock_by_nominal_size(
						required_thickness=line.required_thickness,
						category_code2=line_category,
						nominal_width_m=panel_width_m,
						nominal_length_m=panel_length_m,
						material_code=material_code,
					)

					stock_code = resolved_stock.stock_code if resolved_stock else None
					available_qty = stock_map.get(stock_code) if stock_code else None
					is_sufficient = None
					panel_type_name = _get_panel_type_name(panel_width_m, panel_length_m)

					if stock_code and available_qty is not None:
						is_sufficient = available_qty >= required_qty
						if not is_sufficient:
							shortages.append(
								{
									"stock_code": stock_code,
									"required_qty": float(required_qty),
									"available_qty": float(available_qty),
									"missing_qty": float((required_qty - available_qty).quantize(Decimal("0.001"))),
									"unit": "adet",
								}
							)

					if stock_code is None:
						shortages.append(
							{
								"stock_code": None,
								"required_qty": float(required_qty),
								"available_qty": None,
								"missing_qty": float(required_qty),
								"unit": "adet",
								"reason": f"{line.zone_type} icin {panel_width_m}x{panel_length_m}m ({panel_type_name}) panel stok karsiligi bulunamadi.",
							}
						)

					bom_lines.append(
						{
							"zone_type": line.zone_type,
							"layer_level": float(line.layer_level) if line.layer_level is not None else None,
							"required_thickness": float(line.required_thickness),
							"stock_category": line_category,
							"panel_type": f"{panel_width_m}x{panel_length_m}",
							"panel_type_name": panel_type_name,
							"required_qty": float(required_qty),
							"unit": "adet",
							"stock_code": stock_code,
							"stock_name": resolved_stock.stock_name if resolved_stock else None,
							"available_qty": float(available_qty) if available_qty is not None else None,
							"is_sufficient": is_sufficient,
						}
					)

				continue

			if line.zone_type == "WALL" and line.required_thickness is not None:
				layer_height = layer_height_map.get(line.layer_level, Decimal("1"))
				panel_mix = _calculate_wall_panel_mix(
					width=width,
					length=length,
					layer_height=layer_height,
					multiplier=requirement_multiplier,
				)

				# Ilk duvar katinda manhole girisi icin 1 panel dusulur.
				is_first_wall_layer = first_wall_layer is not None and line.layer_level == first_wall_layer
				if is_first_wall_layer:
					if panel_mix["primary_qty"] > 0:
						panel_mix["primary_qty"] -= Decimal("1")
					elif panel_mix["secondary_qty"] > 0:
						panel_mix["secondary_qty"] -= Decimal("1")

				wall_parts = [
					(panel_mix["primary_type"], panel_mix["primary_qty"]),
					(panel_mix["secondary_type"], panel_mix["secondary_qty"]),
				]

				for panel_type, required_qty in wall_parts:
					if required_qty <= 0:
						continue

					resolved_stock = _resolve_stock_by_thickness_and_size(
						required_thickness=line.required_thickness,
						panel_type=panel_type,
						material_code=material_code,
						category_code2=line_category,
					)

					stock_code = resolved_stock.stock_code if resolved_stock else None
					available_qty = stock_map.get(stock_code) if stock_code else None
					is_sufficient = None

					if stock_code and available_qty is not None:
						is_sufficient = available_qty >= required_qty
						if not is_sufficient:
							shortages.append(
								{
									"stock_code": stock_code,
									"required_qty": float(required_qty),
									"available_qty": float(available_qty),
									"missing_qty": float((required_qty - available_qty).quantize(Decimal("0.001"))),
									"unit": "adet",
								}
							)

					if stock_code is None:
						shortages.append(
							{
								"stock_code": None,
								"required_qty": float(required_qty),
								"available_qty": None,
								"missing_qty": float(required_qty),
								"unit": "adet",
								"reason": f"{panel_type} panel icin uygun stok karti bulunamadi.",
							}
						)

					bom_lines.append(
						{
							"zone_type": line.zone_type,
							"layer_level": float(line.layer_level) if line.layer_level is not None else None,
							"required_thickness": float(line.required_thickness),
							"stock_category": line_category,
							"panel_type": panel_type,
							"required_qty": float(required_qty),
							"unit": "adet",
							"manhole_deducted": is_first_wall_layer,
							"stock_code": stock_code,
							"stock_name": resolved_stock.stock_name if resolved_stock else None,
							"available_qty": float(available_qty) if available_qty is not None else None,
							"is_sufficient": is_sufficient,
						}
					)

				continue
			#burada eğer köşebent bombeliyse gibi bir dallanma eklenmeli
			if line.zone_type == "EXTERNAL_ANGLE" and line.required_thickness is not None:
				# Dış Köşebent - Deponun 4 köşesine atılır.
				required_qty = Decimal("4")
				resolved_stocks = []

				# Kalınlık BOM'dan (line.required_thickness) gelir.
				# Köşebentin boyu deponun maksimum yüksekliği (height) olmalıdır.
				resolved_stock = _resolve_stock_by_nominal_size(
					required_thickness=line.required_thickness,
					category_code2=line_category,
					nominal_width_m=Decimal(),  # Köşebentin uzunluğu = Depo yüksekliği (Örn: 2.16)
					nominal_length_m=height,  # Kendi veritabanı standartlarına göre ayarlayabilirsin
					material_code=material_code,
				)

				if resolved_stock:
					resolved_stocks.append((resolved_stock, required_qty))
				else:
					# Belirtilen ebatta bulunamazsa fallback olarak genel arama
					fallback_stock = _resolve_stock_for_line(
						line,
						material_code=material_code,
						category_code2=line_category,
					)
					if fallback_stock:
						resolved_stocks.append((fallback_stock, required_qty))

				# Her bir stok türü için eksik/yeterli kontrolü yap
				unit = "adet"
				
				# Eğer resolved_stocks boşsa (stok hiç bulunamadıysa) döngüye girmeden hata basmak için:
				if not resolved_stocks:
					shortages.append(
						{
							"stock_code": None,
							"required_qty": float(required_qty),
							"available_qty": None,
							"missing_qty": float(required_qty),
							"unit": unit,
							"reason": f"Dış Köşebent (Kalınlık: {line.required_thickness}mm, Boy: {height}m) için uygun stok kartı bulunamadı.",
						}
					)
					
				for stock_obj, qty in resolved_stocks:
					stock_code = stock_obj.stock_code if stock_obj else None
					available_qty = stock_map.get(stock_code) if stock_code else None
					is_sufficient = None

					if stock_code and available_qty is not None:
						is_sufficient = available_qty >= qty
						if not is_sufficient:
							shortages.append(
								{
									"stock_code": stock_code,
									"required_qty": float(qty),
									"available_qty": float(available_qty),
									"missing_qty": float((qty - available_qty).quantize(Decimal("0.001"))),
									"unit": unit,
								}
							)
					elif stock_code and available_qty is None:
						# Stok kartı var ama envanterde miktar bilgisi yoksa
						shortages.append(
							{
								"stock_code": stock_code,
								"required_qty": float(qty),
								"available_qty": 0.0,
								"missing_qty": float(qty),
								"unit": unit,
								"reason": "Stok bakiyesi bulunamadı."
							}
						)

					bom_lines.append(
						{
							"zone_type": line.zone_type,
							"layer_level": float(line.layer_level) if line.layer_level is not None else None,
							"required_thickness": float(line.required_thickness),
							"stock_category": line_category,
							"required_qty": float(qty),
							"unit": unit,
							"stock_code": stock_code,
							"stock_name": stock_obj.stock_name if stock_obj else None,
							"available_qty": float(available_qty) if available_qty is not None else None,
							"is_sufficient": is_sufficient,
						}
					)

				continue
			if line.zone_type == "INTERNAL_TIE" and line.required_thickness is not None:
				# İç Gergi - Height'a bağlı hesaplama
				required_qty = (height / WALL_MODULE_HEIGHT_M).to_integral_value(rounding=ROUND_CEILING)
				required_qty = required_qty * requirement_multiplier

				# Kalınlıktan stok eşleştirmesi yap
				resolved_stock = _resolve_stock_for_line(
					line,
					material_code=material_code,
					category_code2=line_category,
				)

				stock_code = resolved_stock.stock_code if resolved_stock else None
				available_qty = stock_map.get(stock_code) if stock_code else None
				is_sufficient = None
				unit = "adet"

				if stock_code and available_qty is not None:
					is_sufficient = available_qty >= required_qty
					if not is_sufficient:
						shortages.append(
							{
								"stock_code": stock_code,
								"required_qty": float(required_qty.quantize(Decimal("0.001"))),
								"available_qty": float(available_qty),
								"missing_qty": float((required_qty - available_qty).quantize(Decimal("0.001"))),
								"unit": unit,
							}
						)

				if stock_code is None:
					shortages.append(
						{
							"stock_code": None,
							"required_qty": float(required_qty.quantize(Decimal("0.001"))),
							"available_qty": None,
							"missing_qty": float(required_qty.quantize(Decimal("0.001"))),
							"unit": unit,
							"reason": f"İç Gergi icin uygun stok karti bulunamadi.",
						}
					)

				bom_lines.append(
					{
						"zone_type": line.zone_type,
						"layer_level": float(line.layer_level) if line.layer_level is not None else None,
						"required_thickness": float(line.required_thickness),
						"stock_category": line_category,
						"required_qty": float(required_qty.quantize(Decimal("0.001"))),
						"unit": unit,
						"stock_code": stock_code,
						"stock_name": resolved_stock.stock_name if resolved_stock else None,
						"available_qty": float(available_qty) if available_qty is not None else None,
						"is_sufficient": is_sufficient,
					}
				)

				continue




			resolved_stock = _resolve_stock_for_line(
				line,
				material_code=material_code,
				category_code2=line_category,
			)
			if line.zone_type in {"COVER", "ACCESSORY"}:
				required_area_m2 = None
				sheet_area_m2 = None
				base_required_qty = Decimal("1")
				required_qty = Decimal("1")
			else:
				required_area_m2 = _calculate_required_area_m2(line, width, length)
				sheet_area_m2 = _stock_sheet_area_m2(resolved_stock)
				required_piece_qty = _calculate_required_piece_qty(
					required_area_m2=required_area_m2,
					sheet_area_m2=sheet_area_m2,
					multiplier=requirement_multiplier,
				)

				base_required_qty = required_area_m2.quantize(Decimal("0.001")) if required_area_m2 is not None else Decimal("1")
				required_qty = required_piece_qty

			stock_code = resolved_stock.stock_code if resolved_stock else None
			available_qty = stock_map.get(stock_code) if stock_code else None
			is_sufficient = None
			unit = "adet"

			if stock_code and available_qty is not None and required_qty is not None:
				is_sufficient = available_qty >= required_qty
				if not is_sufficient:
					shortages.append(
						{
							"stock_code": stock_code,
							"required_qty": float(required_qty.quantize(Decimal("0.001"))),
							"available_qty": float(available_qty),
							"missing_qty": float((required_qty - available_qty).quantize(Decimal("0.001"))),
							"unit": unit,
						}
					)

			if stock_code is None:
				shortages.append(
					{
						"stock_code": None,
						"required_qty": float(required_qty.quantize(Decimal("0.001"))) if required_qty is not None else None,
						"available_qty": None,
						"missing_qty": float(required_qty.quantize(Decimal("0.001"))) if required_qty is not None else None,
						"unit": unit,
						"reason": "Bu satir icin uygun stok karti bulunamadi.",
					}
				)

			if stock_code and required_qty is None:
				shortages.append(
					{
						"stock_code": stock_code,
						"required_qty": None,
						"available_qty": float(available_qty) if available_qty is not None else None,
						"missing_qty": None,
						"unit": unit,
						"reason": "Stok kartinda panel ebatlari (bom_width_mm, bom_length_mm) eksik oldugu icin adet hesabi yapilamadi.",
					}
				)

			bom_lines.append(
				{
					"zone_type": line.zone_type,
					"layer_level": float(line.layer_level) if line.layer_level is not None else None,
					"required_thickness": float(line.required_thickness) if line.required_thickness is not None else None,
					"stock_category": line_category,
					"base_required_qty": float(base_required_qty.quantize(Decimal("0.001"))),
					"required_qty": float(required_qty.quantize(Decimal("0.001"))) if required_qty is not None else None,
					"unit": unit,
					"sheet_area_m2": float(sheet_area_m2.quantize(Decimal("0.001"))) if sheet_area_m2 is not None else None,
					"stock_code": stock_code,
					"stock_name": resolved_stock.stock_name if resolved_stock else None,
					"available_qty": float(available_qty) if available_qty is not None else None,
					"is_sufficient": is_sufficient,
				}
			)




		# Aksesuar ve Merdivenler: Height'e göre otomatik seçim ve BOM'a ekleme
		# Tüm aksesuar stoklarını (Dış Merdiven, İç Merdiven, Pabuç vb.) çek
		
		# İç merdiven türünü malzeme tipinden belirle (depo materyaline göre Çelik/GRP)
		
		# Height'e göre uygun merdivenler ve aksesuarları BOM'a ekle
		bom_lines = _add_ladders_to_bom(
			tank_height_m=float(height),
			bom_lines=bom_lines,
			inner_ladder_type="Çelik", # ileride grp ve çelik seçtireceğim.
		)

		payload["matched_header"] = {
			"id": header.id,
			"material_type": header.material_type,
			"tonnage_range": {
				"min": header.min_tonnage,
				"max": header.max_tonnage,
			},
			"selected_module_height": float(selected_height) if selected_height is not None else None,
		}
		payload["bom_lines"] = bom_lines
		payload["warehouse_check"] = {
			"is_available": len(shortages) == 0,
			"shortages": shortages,
		}

		return JsonResponse(payload, status=200)


def _add_ladders_to_bom(tank_height_m, bom_lines, inner_ladder_type="Çelik"):
    """
    Sadece Dış ve İç merdiveni hesaplayıp BOM listesine ekler.
    Aksesuarlar (Pabuç, Kulak vb.) hariç tutulmuştur.
    """
    tank_height_mm = tank_height_m * 1000
    
    # İç merdiven materyali (bom_category_code4)
    inner_ladder_cat4 = "Çelik Yarımamul" if inner_ladder_type == "Çelik" else "Grp Yarımamul"
    
    # 1. DIŞ MERDİVEN SEÇİMİ
    # 'Ortak Yarımamul' olan, boyu >= depo boyu olanların en KISASI
    selected_outer_ladder = StockCard.objects.filter(
        bom_category_code3='Merdiven',
        bom_category_code4='Ortak Yarımamul',
        bom_length_mm__gte=tank_height_mm
    ).order_by('bom_length_mm').first()

    # 2. İÇ MERDİVEN SEÇİMİ
    # Materyale uyan, boyu <= depo boyu olanların en UZUNU
    selected_inner_ladder = StockCard.objects.filter(
        bom_category_code3='Merdiven',
        bom_category_code4=inner_ladder_cat4,
        bom_length_mm__lte=tank_height_mm,
        bom_length_mm__gt=0  # Uzunluğu 0 olan aksesuarlar yanlışlıkla gelmesin diye güvence
    ).order_by('-bom_length_mm').first()

    # Sadece seçilen merdivenleri listeye ekle
    items_to_add = []
    
    if selected_outer_ladder:
        items_to_add.append(selected_outer_ladder)
    if selected_inner_ladder:
        items_to_add.append(selected_inner_ladder)

    # BOM (Ürün Ağacı) Çıktısını Oluştur
    for item in items_to_add:
        bom_lines.append({
            "zone_type": "ACCESSORY",
            "layer_level": None,
            "required_thickness": None,
            "stock_category": item.bom_category_code2,
            "required_qty": float(1.0),
            "unit": item.unit_name or "Adet",
            "stock_code": item.stock_code,
            "stock_name": item.stock_name,
            "available_qty": None,
            "is_sufficient": None,
        })

    return bom_lines