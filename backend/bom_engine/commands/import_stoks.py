
from django.core.management.base import BaseCommand
import csv
import pandas as pd
from bom_engine.models import StokKarti

class Command(BaseCommand):
    help = 'CSV dosyasından stok kartlarını yükler' 
    def handle(self, *args, **options):
        file_path = 'stok_verileri.csv'  # CSV dosyanızın yolu
        # çoklu sayfayı pandas ile oku
        df = pd.read_csv(file_path, delimiter=';')  # Ayırıcıya dikkat!
        for _, row in df.iterrows():
            obj, created = StokKarti.objects.update_or_create(
                sto_kod=row['sto_kod'],
                defaults={
                    'sto_isim': row['sto_isim'],
                    'bom_kategori': row.get('bom_kategori'),
                    'bom_malzeme': row.get('bom_malzeme'),
                    'sto_birim1_ad': row.get('birim', 'Adet'),
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"{obj.sto_kod} eklendi."))