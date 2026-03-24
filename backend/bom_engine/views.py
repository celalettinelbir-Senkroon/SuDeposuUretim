from decimal import Decimal, InvalidOperation

from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .models import ReferenceBomHeader, ReferenceBomLine, StandardCategory


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
