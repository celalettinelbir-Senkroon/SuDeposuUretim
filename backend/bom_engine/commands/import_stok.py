"""
Django Management Command - Multi-Tenant Stok Import

Kurulum:
    Bu dosyayı şuraya kopyalayın: bom_engine/management/commands/import_stok.py
    
    Klasör yapısı:
    bom_engine/
    ├── models.py
    ├── management/
    │   ├── __init__.py          (boş dosya)
    │   └── commands/
    │       ├── __init__.py      (boş dosya)
    │       └── import_stok.py   (bu dosya)

Kullanım:
    # Tenant listesini görüntüle
    python manage.py import_stok --list-tenants
    
    # Belirli bir tenant'a import (test modu)
    python manage.py import_stok --schema customer1 --file "Dizilim Tipleri.xlsx" --dry-run
    
    # Belirli bir tenant'a import (canlı)
    python manage.py import_stok --schema customer1 --file "Dizilim Tipleri.xlsx"
    
    # Tüm tenant'lara import (test modu)
    python manage.py import_stok --all-tenants --file "Dizilim Tipleri.xlsx" --dry-run
    
    # Tüm tenant'lara import (canlı)
    python manage.py import_stok --all-tenants --file "Dizilim Tipleri.xlsx"
"""

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import get_tenant_model, schema_context
import pandas as pd
from decimal import Decimal
import re


class Command(BaseCommand):
    help = 'Excel dosyasından StokKarti modelini doldurur (Multi-tenant destekli)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Import edilecek Excel dosyasının yolu',
        )
        parser.add_argument(
            '--schema',
            type=str,
            help='Tenant schema adı (örn: customer1)',
        )
        parser.add_argument(
            '--all-tenants',
            action='store_true',
            help='Tüm tenant\'lara import yap',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test modu - veritabanına yazma',
        )
        parser.add_argument(
            '--list-tenants',
            action='store_true',
            help='Mevcut tenant\'ları listele',
        )
        parser.add_argument(
            '--exclude-public',
            action='store_true',
            default=True,
            help='Public schema\'yı hariç tut (varsayılan: True)',
        )

    def handle(self, *args, **options):
        # Tenant listesi
        if options['list_tenants']:
            self.list_tenants()
            return

        # Excel dosyası kontrolü
        if not options['file']:
            raise CommandError('--file parametresi gerekli! (--list-tenants hariç)')

        excel_file = options['file']
        dry_run = options['dry_run']

        # Tüm tenant'lara import
        if options['all_tenants']:
            self.import_all_tenants(excel_file, dry_run, options['exclude_public'])
        # Belirli tenant'a import
        elif options['schema']:
            self.import_to_tenant(excel_file, options['schema'], dry_run)
        else:
            raise CommandError(
                'Ya --schema ya da --all-tenants parametresi gerekli!\n'
                'Kullanım: python manage.py import_stok --schema customer1 --file excel.xlsx'
            )

    def list_tenants(self):
        """Mevcut tenant'ları listele"""
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('MEVCUT TENANT\'LAR'))
        self.stdout.write(self.style.SUCCESS('='*80))
        
        Customer = get_tenant_model()
        tenants = Customer.objects.all()
        
        for tenant in tenants:
            name = tenant.name if hasattr(tenant, 'name') else 'N/A'
            domain = tenant.domain_url if hasattr(tenant, 'domain_url') else 'N/A'
            is_public = ' 🔓 PUBLIC' if tenant.schema_name == 'public' else ''
            
            self.stdout.write(
                f"  • Schema: {tenant.schema_name:25s} | "
                f"Ad: {name:30s} | "
                f"Domain: {domain}{is_public}"
            )
        
        self.stdout.write(self.style.SUCCESS('='*80))
        self.stdout.write(f"Toplam: {tenants.count()} tenant\n")

    def import_to_tenant(self, excel_file, schema_name, dry_run):
        """Belirli bir tenant'a import yap"""
        Customer = get_tenant_model()
        
        try:
            tenant = Customer.objects.get(schema_name=schema_name)
        except Customer.DoesNotExist:
            raise CommandError(f"'{schema_name}' schema'sına sahip tenant bulunamadı!")
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*80}'))
        self.stdout.write(self.style.SUCCESS(f'TENANT: {tenant.schema_name}'))
        if hasattr(tenant, 'name'):
            self.stdout.write(f'Ad: {tenant.name}')
        self.stdout.write(self.style.SUCCESS('='*80))
        
        with schema_context(schema_name):
            stats = self.perform_import(excel_file, dry_run, schema_name)
            self.print_summary(stats, dry_run)

    def import_all_tenants(self, excel_file, dry_run, exclude_public):
        """Tüm tenant'lara import yap"""
        Customer = get_tenant_model()
        tenants = Customer.objects.all()
        
        if exclude_public:
            tenants = tenants.exclude(schema_name='public')
        
        tenant_list = list(tenants)
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*80}'))
        self.stdout.write(self.style.SUCCESS(f'TOPLU TENANT IMPORT'))
        self.stdout.write(self.style.SUCCESS(f'Toplam: {len(tenant_list)} tenant'))
        self.stdout.write(self.style.SUCCESS('='*80))
        
        results = {}
        
        for idx, tenant in enumerate(tenant_list, 1):
            self.stdout.write(f'\n[{idx}/{len(tenant_list)}] → Tenant: {tenant.schema_name}')
            
            try:
                with schema_context(tenant.schema_name):
                    stats = self.perform_import(excel_file, dry_run, tenant.schema_name)
                    results[tenant.schema_name] = stats
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Hata: {e}'))
                results[tenant.schema_name] = {'error': str(e)}
        
        # Genel rapor
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('TOPLU IMPORT GENEL RAPORU'))
        self.stdout.write('='*80)
        
        success_count = 0
        error_count = 0
        
        for schema_name, stats in results.items():
            if 'error' in stats:
                error_count += 1
                self.stdout.write(self.style.ERROR(
                    f'✗ {schema_name:25s} - HATA: {stats["error"][:50]}'
                ))
            else:
                success_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'✓ {schema_name:25s} - '
                    f'Başarılı: {stats["basarili"]:3d}, '
                    f'Yeni: {stats.get("yeni", 0):3d}, '
                    f'Güncellenen: {stats.get("guncellenen", 0):3d}'
                ))
        
        self.stdout.write('='*80)
        self.stdout.write(self.style.SUCCESS(f'Başarılı Tenant: {success_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'Hatalı Tenant:   {error_count}'))
        self.stdout.write('='*80 + '\n')

    def perform_import(self, excel_file, dry_run, schema_name=None):
        """Asıl import işlemi"""
        from bom_engine.models import StokKarti
        
        # Excel oku
        try:
            df = pd.read_excel(excel_file, sheet_name='Yarı Mamül ve Mamül Güncel')
        except Exception as e:
            raise CommandError(f"Excel okuma hatası: {e}")
        
        # Temizle
        df = df[df['Htg Mal Kodu'].notna()]
        df = df[~df['Htg Mal Kodu'].astype(str).str.contains(r'\*\*\*', na=False)]
        
        stats = {
            'toplam': len(df),
            'basarili': 0,
            'hatali': 0,
            'yeni': 0,
            'guncellenen': 0,
        }
        
        self.stdout.write(f'  Toplam kayıt: {len(df)}')
        
        for idx, row in df.iterrows():
            try:
                sto_kod = self.clean_value(
                    row.get('Yen Mal Kod'), 
                    self.clean_value(row.get('Htg Mal Kodu'))
                )
                
                if not sto_kod:
                    stats['hatali'] += 1
                    continue
                
                sto_isim = self.clean_value(row.get('Mal Ad'))[:255]
                sto_birim1_ad = self.clean_value(row.get('Birim'), 'Adet')[:20]
                bom_kategori = self.parse_kategori(row)
                bom_malzeme = self.detect_malzeme(row)
                bom_kalinlik_mm = self.parse_kalinlik(row)
                bom_ebat = self.parse_ebat(row)
                
                kayit_durumu = self.clean_value(row.get('Kayıt Durumu'))
                sto_pasif_fl = kayit_durumu != 'Onaylı'
                
                if dry_run:
                    # Test modu - sadece yazdır
                    if idx < 10:  # İlk 10 kayıt
                        status = "PASİF" if sto_pasif_fl else "AKTİF"
                        self.stdout.write(
                            f"  [{status:6s}] {sto_kod:20s} | {sto_isim[:40]:40s}"
                        )
                    stats['basarili'] += 1
                else:
                    # Canlı mod - veritabanına yaz
                    stok, created = StokKarti.objects.update_or_create(
                        sto_kod=sto_kod,
                        defaults={
                            'sto_isim': sto_isim,
                            'sto_birim1_ad': sto_birim1_ad,
                            'bom_kategori': bom_kategori,
                            'bom_malzeme': bom_malzeme,
                            'bom_kalinlik_mm': bom_kalinlik_mm,
                            'bom_ebat': bom_ebat,
                            'sto_pasif_fl': sto_pasif_fl,
                        }
                    )
                    
                    if created:
                        stats['yeni'] += 1
                    else:
                        stats['guncellenen'] += 1
                    
                    stats['basarili'] += 1
                    
            except Exception as e:
                stats['hatali'] += 1
                if stats['hatali'] <= 5:  # İlk 5 hatayı göster
                    self.stdout.write(self.style.WARNING(
                        f'  ✗ Hata ({sto_kod if "sto_kod" in locals() else "N/A"}): {e}'
                    ))
        
        return stats

    def print_summary(self, stats, dry_run):
        """Özet rapor yazdır"""
        self.stdout.write('\n' + '-'*80)
        self.stdout.write(self.style.SUCCESS('İŞLEM RAPORU'))
        self.stdout.write('-'*80)
        self.stdout.write(f"Toplam Kayıt:    {stats['toplam']}")
        self.stdout.write(f"Başarılı:        {stats['basarili']}")
        self.stdout.write(f"Hatalı:          {stats['hatali']}")
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"Yeni Eklenen:    {stats['yeni']}"))
            self.stdout.write(self.style.SUCCESS(f"Güncellenen:     {stats['guncellenen']}"))
        
        self.stdout.write('-'*80)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  TEST MODU - Veritabanına yazılmadı'))
            self.stdout.write('Canlı import için --dry-run parametresini kaldırın\n')
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Import tamamlandı!\n'))

    # Yardımcı fonksiyonlar
    def clean_value(self, value, default=""):
        if pd.isna(value) or value in [':: Seçiniz ::', '::Seçiniz::', '::Yok::', '0 -  ::Seçiniz::']:
            return default
        return str(value).strip()

    def parse_kategori(self, row):
        parts = []
        ana_grup = self.clean_value(row.get('Ana Mal Tip Grubu'))
        if ana_grup:
            parts.append(ana_grup)
        
        alt_grup = self.clean_value(row.get('Ana Mal Tip Alt Grubu'))
        if alt_grup:
            alt_grup = re.sub(r'^\d+\s*-\s*', '', alt_grup)
            parts.append(alt_grup)
        
        cesit = self.clean_value(row.get('Ana Mal Tip Çeşit Grubu'))
        if cesit:
            cesit = re.sub(r'^\d+\s*-\s*', '', cesit)
            parts.append(cesit)
        
        return ' / '.join(parts) if parts else None

    def detect_malzeme(self, row):
        text = ' '.join([
            self.clean_value(row.get('Ana Mal Tip Grubu')),
            self.clean_value(row.get('Mal Ad')),
        ]).lower()
        
        if 'grp' in text or 'polyester' in text:
            return 'GRP'
        elif 'smc' in text:
            return 'SMC'
        elif 'galvaniz' in text or 'galv' in text:
            return 'GALVANIZ'
        elif 'paslanmaz' in text or 'inox' in text or 'aisi' in text:
            return 'PASLANMAZ'
        elif 'alüminyum' in text or 'aluminyum' in text or 'alum' in text:
            return 'ALUMINYUM'
        elif 'bakır' in text or 'copper' in text:
            return 'BAKIR'
        elif 'bronz' in text:
            return 'BRONZ'
        elif 'pirinç' in text or 'brass' in text:
            return 'PIRINC'
        elif 'çelik' in text or 'celik' in text or 'steel' in text:
            return 'CELIK'
        
        return None

    def parse_ebat(self, row):
        en = row.get('En (cm)')
        boy = row.get('Boy (cm)')
        
        if pd.notna(en) and pd.notna(boy):
            try:
                en_val = float(en)
                boy_val = float(boy)
                if en_val > 0 and boy_val > 0:
                    en_m = en_val / 100
                    boy_m = boy_val / 100
                    return f"{en_m:.2f}x{boy_m:.2f}"
            except:
                pass
        return None

    def parse_kalinlik(self, row):
        kalinlik = row.get('Stok Kalınlık')
        
        if pd.notna(kalinlik) and kalinlik != '::Yok::':
            try:
                return Decimal(str(kalinlik))
            except:
                pass
        return None