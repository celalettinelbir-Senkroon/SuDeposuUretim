from django.urls import path

from .views import TankCalculationView, WarehouseRecipeCalculationView

urlpatterns = [
    path("tank/calculate/", TankCalculationView.as_view(), name="tank-calculate"),
    path("tank/warehouse-bom/", WarehouseRecipeCalculationView.as_view(), name="tank-warehouse-bom"),
    path("depo/hesapla-recete/", WarehouseRecipeCalculationView.as_view(), name="depo-hesapla-recete"),
]