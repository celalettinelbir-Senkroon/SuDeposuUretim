"""
Django Management Command - Multi-Tenant Stock Import

Kurulum:
    Bu dosyayı şuraya kopyalayın: bom_engine/management/commands/import_stock.py
    
    Klasör yapısı:
    bom_engine/
    ├── models.py
    ├── management/
    │   ├── __init__.py          (boş dosya)
    │   └── commands/
    │       ├── __init__.py      (boş dosya)
    │       └── import_stock.py  (bu dosya)

Kullanım:
    # Tenant listesini görüntüle
    python manage.py import_stock --list-tenants
    
    # Belirli bir tenant'a import (test modu)
    python manage.py import_stock --schema customer1 --file "Dizilim Tipleri.xlsx" --dry-run
    
    # Belirli bir tenant'a import (canlı)
    python manage.py import_stock --schema customer1 --file "Dizilim Tipleri.xlsx"
    
    # Tüm tenant'lara import (test modu)
    python manage.py import_stock --all-tenants --file "Dizilim Tipleri.xlsx" --dry-run
    
    # Tüm tenant'lara import (canlı)
    python manage.py import_stock --all-tenants --file "Dizilim Tipleri.xlsx"
"""

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import get_tenant_model, schema_context
import pandas as pd
from decimal import Decimal
import re


class Command(BaseCommand):
    help = 'Import StockCard model from Excel file (Multi-tenant support)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Path to Excel file to import',
        )
        parser.add_argument(
            '--schema',
            type=str,
            help='Tenant schema name (e.g., customer1)',
        )
        parser.add_argument(
            '--all-tenants',
            action='store_true',
            help='Import to all tenants',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test mode - do not write to database',
        )
        parser.add_argument(
            '--list-tenants',
            action='store_true',
            help='List available tenants',
        )
        parser.add_argument(
            '--exclude-public',
            action='store_true',
            default=True,
            help='Exclude public schema (default: True)',
        )

    def handle(self, *args, **options):
        # List tenants
        if options['list_tenants']:
            self.list_tenants()
            return

        # Check Excel file
        if not options['file']:
            raise CommandError('--file parameter is required! (except for --list-tenants)')

        excel_file = options['file']
        dry_run = options['dry_run']

        # Import to all tenants
        if options['all_tenants']:
            self.import_all_tenants(excel_file, dry_run, options['exclude_public'])
        # Import to specific tenant
        elif options['schema']:
            self.import_to_tenant(excel_file, options['schema'], dry_run)
        else:
            raise CommandError(
                'Either --schema or --all-tenants parameter is required!\n'
                'Usage: python manage.py import_stock --schema customer1 --file excel.xlsx'
            )

    def list_tenants(self):
        """List available tenants"""
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('AVAILABLE TENANTS'))
        self.stdout.write(self.style.SUCCESS('='*80))
        
        Customer = get_tenant_model()
        tenants = Customer.objects.all()
        
        for tenant in tenants:
            name = tenant.name if hasattr(tenant, 'name') else 'N/A'
            domain = tenant.domain_url if hasattr(tenant, 'domain_url') else 'N/A'
            is_public = ' 🔓 PUBLIC' if tenant.schema_name == 'public' else ''
            
            self.stdout.write(
                f"  • Schema: {tenant.schema_name:25s} | "
                f"Name: {name:30s} | "
                f"Domain: {domain}{is_public}"
            )
        
        self.stdout.write(self.style.SUCCESS('='*80))
        self.stdout.write(f"Total: {tenants.count()} tenants\n")

    def import_to_tenant(self, excel_file, schema_name, dry_run):
        """Import to specific tenant"""
        Customer = get_tenant_model()
        
        try:
            tenant = Customer.objects.get(schema_name=schema_name)
        except Customer.DoesNotExist:
            raise CommandError(f"Tenant with schema '{schema_name}' not found!")
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*80}'))
        self.stdout.write(self.style.SUCCESS(f'TENANT: {tenant.schema_name}'))
        if hasattr(tenant, 'name'):
            self.stdout.write(f'Name: {tenant.name}')
        self.stdout.write(self.style.SUCCESS('='*80))
        
        with schema_context(schema_name):
            stats = self.perform_import(excel_file, dry_run, schema_name)
            self.print_summary(stats, dry_run)

    def import_all_tenants(self, excel_file, dry_run, exclude_public):
        """Import to all tenants"""
        Customer = get_tenant_model()
        tenants = Customer.objects.all()
        
        if exclude_public:
            tenants = tenants.exclude(schema_name='public')
        
        tenant_list = list(tenants)
        
        self.stdout.write(self.style.SUCCESS(f'\n{"="*80}'))
        self.stdout.write(self.style.SUCCESS(f'BULK TENANT IMPORT'))
        self.stdout.write(self.style.SUCCESS(f'Total: {len(tenant_list)} tenants'))
        self.stdout.write(self.style.SUCCESS('='*80))
        
        results = {}
        
        for idx, tenant in enumerate(tenant_list, 1):
            self.stdout.write(f'\n[{idx}/{len(tenant_list)}] → Tenant: {tenant.schema_name}')
            
            try:
                with schema_context(tenant.schema_name):
                    stats = self.perform_import(excel_file, dry_run, tenant.schema_name)
                    results[tenant.schema_name] = stats
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {e}'))
                results[tenant.schema_name] = {'error': str(e)}
        
        # General report
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('BULK IMPORT SUMMARY'))
        self.stdout.write('='*80)
        
        success_count = 0
        error_count = 0
        
        for schema_name, stats in results.items():
            if 'error' in stats:
                error_count += 1
                self.stdout.write(self.style.ERROR(
                    f'✗ {schema_name:25s} - ERROR: {stats["error"][:50]}'
                ))
            else:
                success_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'✓ {schema_name:25s} - '
                    f'Success: {stats["success"]:3d}, '
                    f'New: {stats.get("new", 0):3d}, '
                    f'Updated: {stats.get("updated", 0):3d}'
                ))
        
        self.stdout.write('='*80)
        self.stdout.write(self.style.SUCCESS(f'Successful Tenants: {success_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'Failed Tenants:     {error_count}'))
        self.stdout.write('='*80 + '\n')

    def perform_import(self, excel_file, dry_run, schema_name=None):
        """Actual import operation"""
        from bom_engine.models import StockCard
        
        # Read Excel
        try:
            df = pd.read_excel(excel_file, sheet_name='Yarı Mamül ve Mamül Güncel')
        except Exception as e:
            raise CommandError(f"Excel read error: {e}")
        
        # Clean data
        df = df[df['Htg Mal Kodu'].notna()]
        df = df[~df['Htg Mal Kodu'].astype(str).str.contains(r'\*\*\*', na=False)]
        
        stats = {
            'total': len(df),
            'success': 0,
            'error': 0,
            'new': 0,
            'updated': 0,
        }
        
        self.stdout.write(f'  Total records: {len(df)}')
        
        for idx, row in df.iterrows():
            try:
                stock_code = self.clean_value(
                    row.get('Yen Mal Kod'), 
                    self.clean_value(row.get('Htg Mal Kodu'))
                )
                
                if not stock_code:
                    stats['error'] += 1
                    continue
                
                stock_name = self.clean_value(row.get('Mal Ad'))[:255]
                unit_name = self.clean_value(row.get('Birim'), 'Piece')[:20]
                bom_category = self.parse_kategori(row)
                bom_material = self.detect_malzeme(row)
                bom_thickness_mm = self.parse_kalinlik(row)
                bom_dimensions = self.parse_ebat(row)
                
                kayit_durumu = self.clean_value(row.get('Kayıt Durumu'))
                is_passive = kayit_durumu != 'Onaylı'
                
                if dry_run:
                    # Test mode - only print
                    if idx < 10:  # First 10 records
                        status = "PASSIVE" if is_passive else "ACTIVE"
                        self.stdout.write(
                            f"  [{status:7s}] {stock_code:20s} | {stock_name[:40]:40s}"
                        )
                    stats['success'] += 1
                else:
                    # Live mode - write to database
                    stock, created = StockCard.objects.update_or_create(
                        stock_code=stock_code,
                        defaults={
                            'stock_name': stock_name,
                            'unit_name': unit_name,
                            'bom_category': bom_category,
                            'bom_material': bom_material,
                            'bom_thickness_mm': bom_thickness_mm,
                            'bom_dimensions': bom_dimensions,
                            'is_passive': is_passive,
                        }
                    )
                    
                    if created:
                        stats['new'] += 1
                    else:
                        stats['updated'] += 1
                    
                    stats['success'] += 1
                    
            except Exception as e:
                stats['error'] += 1
                if stats['error'] <= 5:  # Show first 5 errors
                    self.stdout.write(self.style.WARNING(
                        f'  ✗ Error ({stock_code if "stock_code" in locals() else "N/A"}): {e}'
                    ))
        
        return stats

    def print_summary(self, stats, dry_run):
        """Print summary report"""
        self.stdout.write('\n' + '-'*80)
        self.stdout.write(self.style.SUCCESS('OPERATION REPORT'))
        self.stdout.write('-'*80)
        self.stdout.write(f"Total Records:   {stats['total']}")
        self.stdout.write(f"Successful:      {stats['success']}")
        self.stdout.write(f"Failed:          {stats['error']}")
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"New Created:     {stats['new']}"))
            self.stdout.write(self.style.SUCCESS(f"Updated:         {stats['updated']}"))
        
        self.stdout.write('-'*80)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  TEST MODE - Not written to database'))
            self.stdout.write('Remove --dry-run parameter for live import\n')
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ Import completed!\n'))

    # Helper functions
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