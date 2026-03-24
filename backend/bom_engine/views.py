from decimal import Decimal, InvalidOperation, ROUND_CEILING

from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .models import ReferenceBomHeader, ReferenceBomLine, StandardCategory, StockCard


WALL_MODULE_HEIGHT_M = Decimal("0.5")


def _to_decimal(value):
	try:
		return Decimal(str(value))
	except (InvalidOperation, ValueError, TypeError):
		return None


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


def _resolve_stock_for_line(line, material_code=None):
	"""
	BOM satırında belirtilen kalınlığa göre uygun StockCard'ı bulur.
	Tercih sırası:
	1. Material code ile match (varsa)
	2. Kalınlığa göre (bom_thickness_mm)
	3. is_passive false olanlar önce (aktif stoklar)
	"""
	if line.required_thickness is None:
		return None

	queryset = StockCard.objects.filter(
		bom_thickness_mm=line.required_thickness,
	)

	if material_code:
		queryset = queryset.filter(
			bom_category_code1__icontains=material_code
		) | queryset.filter(
			bom_category_code2__icontains=material_code
		) | queryset.filter(
			bom_category_code3__icontains=material_code
		) | queryset.filter(
			bom_category_code4__icontains=material_code
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

		for line in selected_lines:
			resolved_stock = _resolve_stock_for_line(line, material_code=material_code)
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
