from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .services import calculate_tank, calculate_warehouse_recipe
from .utils import _to_decimal


class TankCalculationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        width_raw = request.data.get("en", request.data.get("width"))
        length_raw = request.data.get("boy", request.data.get("length"))
        height_raw = request.data.get("yukseklik", request.data.get("height"))
        standard_raw = request.data.get("standart", request.data.get("standard"))

        if width_raw is None or length_raw is None or height_raw is None or not standard_raw:
            return JsonResponse({"detail": "'en', 'boy', 'yukseklik' ve 'standart' alanlari zorunludur."}, status=400)

        try:
            width = Decimal(str(width_raw))
            length = Decimal(str(length_raw))
            height = Decimal(str(height_raw))
        except (InvalidOperation, ValueError, TypeError):
            return JsonResponse({"detail": "'en', 'boy' ve 'yukseklik' sayisal bir deger olmali."}, status=400)

        if width <= 0 or length <= 0 or height <= 0:
            return JsonResponse({"detail": "'en', 'boy' ve 'yukseklik' sifirdan buyuk olmali."}, status=400)

        payload = calculate_tank(width, length, height, standard_raw)
        return JsonResponse(payload, status=200)


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
            return JsonResponse({"detail": "'en', 'boy', 'yukseklik' ve 'standart' alanlari zorunludur."}, status=400)

        width = _to_decimal(width_raw)
        length = _to_decimal(length_raw)
        height = _to_decimal(height_raw)

        if width is None or length is None or height is None:
            return JsonResponse({"detail": "'en', 'boy' ve 'yukseklik' sayisal bir deger olmali."}, status=400)

        if width <= 0 or length <= 0 or height <= 0:
            return JsonResponse({"detail": "'en', 'boy' ve 'yukseklik' sifirdan buyuk olmali."}, status=400)

        payload = calculate_warehouse_recipe(
            width, length, height, standard_raw, material_raw, tank_type_raw, warehouse_stocks
        )
        return JsonResponse(payload, status=200)