from django.urls import path

from .views import TankCalculationView

urlpatterns = [
    path("tank/calculate/", TankCalculationView.as_view(), name="tank-calculate"),
]