from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from .models import ReferenceBomHeader, ReferenceBomLine, StandardCategory, StockCard


class WarehouseRecipeCalculationViewTests(TestCase):
	def setUp(self):
		self.client = APIClient()

		self.category = StandardCategory.objects.create(name="Ekomaxi Standartlari")
		self.header = ReferenceBomHeader.objects.create(
			category=self.category,
			material_type="Pre Galvaniz-SDG",
			min_tonnage=0,
			max_tonnage=300,
		)

		ReferenceBomLine.objects.create(
			bom_header=self.header,
			total_module_height=Decimal("2.0"),
			zone_type="BASE",
			required_thickness=Decimal("2.00"),
		)
		ReferenceBomLine.objects.create(
			bom_header=self.header,
			total_module_height=Decimal("2.0"),
			zone_type="WALL",
			layer_level=Decimal("0.5"),
			required_thickness=Decimal("3.00"),
		)

		StockCard.objects.create(
			stock_code="SAC-2MM",
			stock_name="SAC BASE 2MM",
			bom_thickness_mm=Decimal("2.00"),
			is_passive=False,
		)
		StockCard.objects.create(
			stock_code="SAC-3MM",
			stock_name="SAC WALL 3MM",
			bom_thickness_mm=Decimal("3.00"),
			is_passive=False,
		)

	def test_returns_bom_and_marks_available_when_stock_is_enough(self):
		response = self.client.post(
			"/api/bom/depo/hesapla-recete/",
			{
				"en": 2,
				"boy": 3,
				"yukseklik": 2,
				"standart": "Ekomaxi Standartlari",
				"depo_stoklari": [
					{"stock_code": "SAC-2MM", "qty": 10},
					{"stock_code": "SAC-3MM", "qty": 10},
				],
			},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.data["standard_found"])
		self.assertTrue(response.data["warehouse_check"]["is_available"])
		self.assertEqual(len(response.data["bom_lines"]), 2)

	def test_returns_shortage_when_stock_is_not_enough(self):
		response = self.client.post(
			"/api/bom/tank/warehouse-bom/",
			{
				"en": 2,
				"boy": 3,
				"yukseklik": 2,
				"standart": "Ekomaxi Standartlari",
				"depo_stoklari": [
					{"stock_code": "SAC-2MM", "qty": 1},
					{"stock_code": "SAC-3MM", "qty": 1},
				],
			},
			format="json",
		)

		self.assertEqual(response.status_code, 200)
		self.assertFalse(response.data["warehouse_check"]["is_available"])
		self.assertGreaterEqual(len(response.data["warehouse_check"]["shortages"]), 1)
