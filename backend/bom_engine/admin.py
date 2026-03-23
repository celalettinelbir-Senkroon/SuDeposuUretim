from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    StockCard, 
    StandardCategory, 
    ReferenceBomHeader, 
    ReferenceBomLine
)
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin

# @admin.register(StockCard)
# class StockCardAdmin(admin.ModelAdmin):
#     # Listeleme ekranında görünecek kolonlar
#     list_display = (
#         'stock_code_tr',
#         'stock_name_tr',
#         'bom_category_tr',
#         'bom_material_tr',
#         'bom_thickness_mm_tr',
#         'is_passive_tr',
#     )
    
#     # Arama çubuğu (Stok seçerken autocomplete çalışması için çok kritik)
#     search_fields = ('stock_code', 'stock_name')
    
#     # Sağ taraftaki filtreleme menüsü
#     list_filter = ('bom_category', 'bom_material', 'is_passive')
#     ordering = ('stock_code',)

#     @admin.display(description="Stok Kodu", ordering='stock_code')
#     def stock_code_tr(self, obj):
#         return obj.stock_code

#     @admin.display(description="Stok Adı", ordering='stock_name')
#     def stock_name_tr(self, obj):
#         return obj.stock_name

#     @admin.display(description="BOM Kategorisi", ordering='bom_category')
#     def bom_category_tr(self, obj):
#         return obj.bom_category

#     @admin.display(description="BOM Malzemesi", ordering='bom_material')
#     def bom_material_tr(self, obj):
#         return obj.get_bom_material_display() if obj.bom_material else "-"

#     @admin.display(description="BOM Kalınlığı (mm)", ordering='bom_thickness_mm')
#     def bom_thickness_mm_tr(self, obj):
#         return obj.bom_thickness_mm

#     @admin.display(description="Pasif mi?", ordering='is_passive', boolean=True)
#     def is_passive_tr(self, obj):
#         return obj.is_passive


@admin.register(StandardCategory)
class StandardCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active_tr', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)

    @admin.display(description="Aktif mi?", ordering='is_active', boolean=True)
    def is_active_tr(self, obj):
        return obj.is_active


class ReferenceBomLineInline(admin.TabularInline):
    model = ReferenceBomLine
    extra = 1  # Varsayılan olarak eklenecek boş satır sayısı
    verbose_name = "Referans BOM Satırı"
    verbose_name_plural = "Referans BOM Satırları"
    
    # Mükemmel Performans İçin: Stokları selectbox yerine arama kutusu yapar.
    # Binlerce stok kartı olduğunda sayfanın çökmesini engeller.
    autocomplete_fields = ['stock_card']
    
    # Satırların hangi sırayla dizileceği (Önce kat yüksekliği, sonra bölge, sonra katman)
    ordering = ('total_module_height', 'zone_type', 'layer_level')


@admin.register(ReferenceBomHeader)
class ReferenceBomHeaderAdmin(admin.ModelAdmin):
    # Ana tablo listesi
    list_display = (
        'category_tr',
        'material_type_tr',
        'min_tonnage_tr',
        'max_tonnage_tr',
        'created_at',
    )
    list_filter = ('category', 'material_type')
    search_fields = ('category__name', 'material_type')
    
    # Satırları ana formun içine gömme
    inlines = [ReferenceBomLineInline]
    
    fieldsets = (
        (_('Kategori ve Malzeme'), {
            'fields': ('category', 'material_type')
        }),
        (_('Tonaj Aralığı'), {
            'fields': (('min_tonnage', 'max_tonnage'),)
        }),
    )

    @admin.display(description="Kategori", ordering='category__name')
    def category_tr(self, obj):
        return obj.category

    @admin.display(description="Malzeme Tipi", ordering='material_type')
    def material_type_tr(self, obj):
        return obj.material_type

    @admin.display(description="Minimum Tonaj", ordering='min_tonnage')
    def min_tonnage_tr(self, obj):
        return obj.min_tonnage

    @admin.display(description="Maksimum Tonaj", ordering='max_tonnage')
    def max_tonnage_tr(self, obj):
        return obj.max_tonnage


admin.site.site_header = "Water Warehouse Yönetim Paneli"
admin.site.site_title = "Water Warehouse Admin"
admin.site.index_title = "Yönetim"



class StockCardResource(resources.ModelResource):
    # Excel'deki sütun başlıkları (column_name) ile modeldeki alanları (attribute) eşleştiriyoruz
    stock_code = fields.Field(column_name='Stok Kodu', attribute='stock_code')
    stock_name = fields.Field(column_name='Stok Adı', attribute='stock_name')
    unit_name = fields.Field(column_name='Birim', attribute='unit_name')
    bom_category = fields.Field(column_name='Kategori', attribute='bom_category')
    bom_thickness_mm = fields.Field(column_name='Kalınlık', attribute='bom_thickness_mm')

    class Meta:
        model = StockCard
        import_id_fields = ('stock_code',)  # Stok koduna göre güncelleme yapar
        skip_unchanged = True
        report_skipped = True

    def before_import_row(self, row, **kwargs):
        """Excel'den gelen kirli veriyi veritabanına yazmadan önce temizler."""
        kalinlik_verisi = row.get('Kalınlık')
        if kalinlik_verisi:
            # '1,00 mm' formatındaki veriyi float'a çevirilebilir hale getirir
            temiz_veri = str(kalinlik_verisi).lower().replace('mm', '').replace(',', '.').strip()
            try:
                row['Kalınlık'] = float(temiz_veri)
            except ValueError:
                row['Kalınlık'] = None
                
                
# admin.ModelAdmin yerine ImportExportModelAdmin yazıyoruz
@admin.register(StockCard)
class StockCardAdmin(ImportExportModelAdmin): 
    # Yazdığımız resource sınıfını buraya bağlıyoruz
    resource_classes = [StockCardResource] 

    # --- AŞAĞIDAKİ KISIMLAR SİZİN ORİJİNAL KODLARINIZ (HİÇ DEĞİŞMEDİ) ---
    list_display = (
        'stock_code_tr',
        'stock_name_tr',
        'bom_category_tr',
        'bom_material_tr',
        'bom_thickness_mm_tr',
        'is_passive_tr',
    )
    
    search_fields = ('stock_code', 'stock_name')
    list_filter = ('bom_category', 'bom_material', 'is_passive')
    ordering = ('stock_code',)

    @admin.display(description="Stok Kodu", ordering='stock_code')
    def stock_code_tr(self, obj):
        return obj.stock_code

    @admin.display(description="Stok Adı", ordering='stock_name')
    def stock_name_tr(self, obj):
        return obj.stock_name

    @admin.display(description="BOM Kategorisi", ordering='bom_category')
    def bom_category_tr(self, obj):
        return obj.bom_category

    @admin.display(description="BOM Malzemesi", ordering='bom_material')
    def bom_material_tr(self, obj):
        return obj.get_bom_material_display() if obj.bom_material else "-"

    @admin.display(description="BOM Kalınlığı (mm)", ordering='bom_thickness_mm')
    def bom_thickness_mm_tr(self, obj):
        return obj.bom_thickness_mm

    @admin.display(description="Pasif mi?", ordering='is_passive', boolean=True)
    def is_passive_tr(self, obj):
        return obj.is_passive