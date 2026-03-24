from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal

# Kendi uygulama adınızı buraya yazın
from bom_engine.models import StandardCategory, ReferenceBomHeader, ReferenceBomLine

class Command(BaseCommand):
    help = 'Ekomaxi 0-300 Ton matrisini veritabanına yükler.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Matris verileri yükleniyor...'))

        # 1. Kategori ve Başlığı Oluştur
        category, _ = StandardCategory.objects.get_or_create(
            name="Ekomaxi Standartları",
            defaults={"description": "Ekomaxi modüler su deposu mühendislik matrisleri"}
        )

        header, _ = ReferenceBomHeader.objects.get_or_create(
            category=category,
            material_type="Pre Galvaniz-SDG",
            defaults={"min_tonnage": 0, "max_tonnage": 300}
        )

        # Eski verileri temizle (Güncelleme yaparken üst üste binmemesi için)
        ReferenceBomLine.objects.filter(bom_header=header).delete()

        # 2. Matris Verisi
        matrix_data = {
            Decimal('0.5'): {'base': '1.50', 'roof': '0.80', 'cover': '2.00', 'walls': {Decimal('0.5'): '1.50'}},
            Decimal('1.0'): {'base': '1.50', 'roof': '0.80', 'cover': '2.00', 'walls': {Decimal('0.5'): '1.50', Decimal('1.0'): '1.50'}},
            Decimal('1.5'): {'base': '1.50', 'roof': '0.80', 'cover': '2.00', 'walls': {Decimal('0.5'): '2.00', Decimal('1.0'): '2.00', Decimal('1.5'): '1.50'}},
            Decimal('2.0'): {'base': '2.00', 'roof': '0.80', 'cover': '2.00', 'walls': {Decimal('0.5'): '2.00', Decimal('1.0'): '2.00', Decimal('1.5'): '2.00', Decimal('2.0'): '1.50'}},
            Decimal('2.5'): {'base': '2.00', 'roof': '0.80', 'cover': '2.00', 'walls': {Decimal('0.5'): '3.00', Decimal('1.0'): '3.00', Decimal('1.5'): '2.00', Decimal('2.0'): '2.00', Decimal('2.5'): '1.50'}},
            Decimal('3.0'): {'base': '2.00', 'roof': '0.80', 'cover': '2.00', 'walls': {Decimal('0.5'): '3.00', Decimal('1.0'): '3.00', Decimal('1.5'): '2.00', Decimal('2.0'): '2.00', Decimal('2.5'): '1.50', Decimal('3.0'): '1.50'}},
            Decimal('3.5'): {'base': '2.00', 'roof': '0.80', 'cover': '2.00', 'walls': {Decimal('0.5'): '3.00', Decimal('1.0'): '3.00', Decimal('1.5'): '3.00', Decimal('2.0'): '3.00', Decimal('2.5'): '2.00', Decimal('3.0'): '2.00', Decimal('3.5'): '1.50'}},
            Decimal('4.0'): {'base': '2.50', 'roof': '0.80', 'cover': '2.00', 'walls': {Decimal('0.5'): '3.00', Decimal('1.0'): '3.00', Decimal('1.5'): '3.00', Decimal('2.0'): '3.00', Decimal('2.5'): '2.00', Decimal('3.0'): '2.00', Decimal('3.5'): '1.50', Decimal('4.0'): '1.50'}},
        }

        lines_to_create = []

        # 3. Objeleri Hazırla
        for total_height, data in matrix_data.items():
            lines_to_create.extend([
                ReferenceBomLine(bom_header=header, total_module_height=total_height, zone_type='BASE', required_thickness=Decimal(data['base'])),
                ReferenceBomLine(bom_header=header, total_module_height=total_height, zone_type='ROOF', required_thickness=Decimal(data['roof'])),
                ReferenceBomLine(bom_header=header, total_module_height=total_height, zone_type='COVER', required_thickness=Decimal(data['cover'])),
            ])

            for layer, thickness in data['walls'].items():
                lines_to_create.append(
                    ReferenceBomLine(bom_header=header, total_module_height=total_height, zone_type='WALL', layer_level=layer, required_thickness=Decimal(thickness))
                )

        # 4. Veritabanına Toplu Yazma
        with transaction.atomic():
            ReferenceBomLine.objects.bulk_create(lines_to_create)

        self.stdout.write(self.style.SUCCESS(f"Başarılı! {header} için toplam {len(lines_to_create)} adet reçete satırı oluşturuldu."))