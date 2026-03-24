from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from .models import (
    StockCard, 
    VariantMapping,
    StandardCategory, 
    ReferenceBomHeader, 
    ReferenceBomLine
)

# ==========================================
# 1. ANA VERİ (MASTER DATA) - IMPORT/EXPORT İLE
# ==========================================

from import_export import resources, fields

# Kategori Eşleştirme Sözlüğü (Excel'den gelen -> Veritabanına yazılacak)
CATEGORY_MAPPING = {
    "1 - Duvar Panelleri": "duvar_paneli",
    "2 - Düz Taban Panlleri": "duz_taban_paneli",
    "3 - Bombeli Taban Panelleri": "bombeli_taban_paneli",
    "4 - Tavan Panelleri": "tavan_paneli",
    "5 - Bölme Panelleri": "bolme_paneli",
    "8 - Kapaklı Duvar Paneli": "kapakli_duvar_paneli",
    "6 - İçten Takviye": "icten_takviye",
    "7 - Dıştan Takviye": "distan_takviye",
    "70 - Kaide Ara Bağlantı": "kaide_ara_baglanti",
    "71 - Kaide Ekli Bağlantı": "kaide_ekli_baglanti",
    "72 - Kaide Tekli Bağlantı": "kaide_tekli_baglanti",
    "73 - Kaide Birleştirme": "kaide_birlestirme",
    "21 - Aksesuarlar": "aksesuar",
}

class StockCardResource(resources.ModelResource):
    stock_code = fields.Field(column_name='Yen Mal Kod', attribute='stock_code')
    stock_code_1 = fields.Field(column_name='Yen Mal Kod 1', attribute='stock_code_1')
    stock_name = fields.Field(column_name='Mal Ad', attribute='stock_name')
    unit_name = fields.Field(column_name='Birim', attribute='unit_name')
    bom_thickness_mm = fields.Field(column_name='Stok Kalınlık', attribute='bom_thickness_mm')
    bom_width_mm = fields.Field(column_name='En (cm)', attribute='bom_width_mm')
    bom_length_mm = fields.Field(column_name='Boy (cm)', attribute='bom_length_mm')
    bom_category_code1 = fields.Field(column_name='BOM Kategori Kodu 1', attribute='bom_category_code1')
    
    # YENİ EKLENEN ALAN: Sütun adını kendi Excel'ine göre güncelle!
    bom_category_code2 = fields.Field(column_name='BOM Kategori Kodu 2', attribute='bom_category_code2')
    
    is_passive = fields.Field(column_name='Pasif mi?', attribute='is_passive')
    
    class Meta:
        model = StockCard
        import_id_fields = ('stock_code',)
        skip_unchanged = True
        report_skipped = True

    def skip_row(self, instance, original, row, import_validation_errors=None):
        """Excel'deki başlık/grup satırlarını (turuncu satır gibi) atlamak için kullanılır."""
        mal_ad = str(row.get('Mal Ad', '')).strip()
        if not row.get('Birim') or mal_ad.startswith('***'):
            return True
        return super().skip_row(instance, original, row, import_validation_errors)

    def before_import_row(self, row, **kwargs):
        """Veriler veritabanına yazılmadan önce temizleme ve dönüşüm işlemleri yapılır."""
        
        # 1. Sayısal Değerleri Temizleme ve Hesaplama
        def clean_number(val):
            if not val or str(val).strip() == '':
                return None
            if isinstance(val, (int, float)):
                return float(val)
            val_str = str(val).replace(',', '.').strip()
            try:
                return float(val_str)
            except ValueError:
                return None

        thickness = clean_number(row.get('Stok Kalınlık'))
        row['Stok Kalınlık'] = thickness
        
        en_cm = clean_number(row.get('En (cm)'))
        row['En (cm)'] = en_cm * 10 if en_cm is not None else None

        boy_cm = clean_number(row.get('Boy (cm)'))
        row['Boy (cm)'] = boy_cm * 10 if boy_cm is not None else None

        # 2. Kategori Verisini Eşleştirme (Mapping) İşlemi
        # Sütun adını kendi Excel'indeki başlığa göre değiştirmeyi unutma!
        excel_category_column = 'BOM Kategori Kodu 2' 
        
        raw_category = row.get(excel_category_column)
        
        if raw_category:
            raw_category_str = str(raw_category).strip()
            # Sözlükte arar, bulursa temiz halini (örn: 'duvar_paneli') yazar.
            # Eğer sözlükte karşılığı yoksa (beklenmeyen bir veri geldiyse) None atar.
            clean_category = CATEGORY_MAPPING.get(raw_category_str, None)
            row[excel_category_column] = clean_category



@admin.register(StockCard)
class StockCardAdmin(ImportExportModelAdmin):
    resource_classes = [StockCardResource]
    
    list_display = (
        'stock_code', 
        'stock_name', 
        'unit_name', 
        'bom_thickness_mm', 
        'bom_width_mm', 
        'bom_length_mm', 
        'bom_category_code1',
        'is_passive'
    )
    search_fields = ('stock_code', 'stock_name') # autocomplete_fields için kritik!
    list_filter = ('is_passive', 'unit_name', 'bom_category_code1')
    ordering = ('stock_code',)
# ==========================================
# 2. VARYANT ÇEVİRMENİ
# ==========================================

@admin.register(VariantMapping)
class VariantMappingAdmin(admin.ModelAdmin):
    # Sadece mevcut modellerinizdeki alanları listeledik
    list_display = ('produced_stock', 'material_type', 'description')
    search_fields = ('produced_stock__stock_code', 'produced_stock__stock_name', 'material_type', 'description')
    list_filter = ('material_type',)
    
    # PERFORMANS: Binlerce stok olacağı için dropdown yerine arama çubuğu koyuyoruz
    autocomplete_fields = ['produced_stock']


# ==========================================
# 3. REFERANS ŞABLONLARI (KURAL MOTORU)
# ==========================================

@admin.register(StandardCategory)
class StandardCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    # is_active alanı zaten BooleanField olduğu için Django otomatik ikon koyacaktır, özel fonksiyona gerek kalmadı.


class ReferenceBomLineInline(admin.TabularInline):
    model = ReferenceBomLine
    extra = 0  # Ekranı temiz tutmak için 0 yapıldı
    verbose_name = "Referans BOM Satırı"
    verbose_name_plural = "Referans BOM Satırları"
    
    fields = ('total_module_height', 'zone_type', 'layer_level', 'required_thickness', 'stock_card')
    
    # StockCardAdmin içinde search_fields tanımlı olduğu için bu sorunsuz çalışacaktır
    autocomplete_fields = ['stock_card']
    ordering = ('total_module_height', 'zone_type', 'layer_level')


@admin.register(ReferenceBomHeader)
class ReferenceBomHeaderAdmin(admin.ModelAdmin):
    # standard_name kaldırıldı, orijinal modelinizdeki tonajlar eklendi
    list_display = (
        'category',
        'material_type',
        'min_tonnage',
        'max_tonnage',
        'created_at',
    )
    list_filter = ('category', 'material_type')
    search_fields = ('category__name', 'material_type')
    
    inlines = [ReferenceBomLineInline]


# ==========================================
# 4. ADMIN PANELİ ÖZELLEŞTİRMELERİ
# ==========================================

admin.site.site_header = "Water Warehouse Yönetim Paneli"
admin.site.site_title = "Water Warehouse Admin"
admin.site.index_title = "Yönetim"