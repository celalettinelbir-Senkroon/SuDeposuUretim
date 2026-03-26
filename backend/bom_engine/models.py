from django.db import models

# Create your models here.
from django.db import models
import uuid
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

# SEÇENEKLER (CHOICES) - Gelecekte buraya ekleme yapabilirsin
MATERIAL_CHOICES = [
    ('AISI304', 'Paslanmaz AISI 304'),
    ('AISI316', 'Paslanmaz AISI 316'),
    ('SDG', 'Sıcak Daldırma Galvaniz'),
    ('PREGALVANIZ', 'Pre-Galvaniz'),
]

TANK_STANDARDS = [
    ('EKOMAXI', 'Ekomaxi Standart'),
    ('CEVRE_SEHIRCILIK', 'Çevre Şehircilik Standartı'),
]

BASE_TYPES = [
    ('DUZ', 'Düz Taban'),
    ('BOMBELI', 'Bombeli Taban'),
]

import uuid
from django.db import models

class StockCard(models.Model):
    # Mikro Base Fields
    stock_guid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    stock_code = models.CharField(max_length=100, primary_key=True, verbose_name="Stock Code")
    stock_code_1 = models.CharField(max_length=100, verbose_name="Stock Code 1", blank=True, null=True)
    
    stock_name = models.CharField(max_length=255, verbose_name="Stock Name")
    unit_name = models.CharField(max_length=20, default="Piece", verbose_name="Unit Name")
    
    # Engineering / BOM Parameters (To be fed from Mikro Special fields)
    bom_thickness_mm = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name="BOM Thickness (mm)"
    )
    
    bom_width_mm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="BOM Width (mm)",
    )
    
    bom_length_mm = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="BOM Length (mm)",
    )
    bom_category_code1 = models.CharField(max_length=50, blank=True, null=True, verbose_name="BOM Category Code 1")
    bom_category_code2 = models.CharField(max_length=50, blank=True, null=True, verbose_name="BOM Category Code 2")
    bom_category_code3 = models.CharField(max_length=50, blank=True, null=True, verbose_name="BOM Category Code 3")
    bom_category_code4 = models.CharField(max_length=50, blank=True, null=True, verbose_name="BOM Category Code 4")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Price")
    is_passive = models.BooleanField(default=True, verbose_name="Is Passive?")

    class Meta:
        verbose_name = "Stock Card"
        verbose_name_plural = "1. Stock Cards"

    def __str__(self):
        return f"{self.stock_code} | {self.stock_name}"


class VariantMapping(models.Model):
    """
    Hesaplama motoru çalıştığında, istenen kalınlık, ebat ve malzemeye göre
    Mikro'daki HANGİ stok kartının kullanılacağını bulan köprü tablodur.
    """
    produced_stock = models.ForeignKey(StockCard, on_delete=models.CASCADE, related_name='variants', verbose_name="Üretilecek Nihai Stok")
    
    # Arama Kriterleri
    material_type = models.CharField(max_length=100, choices=MATERIAL_CHOICES, db_index=True, verbose_name="Malzeme Tipi")
    # thickness = models.DecimalField(max_digits=5, decimal_places=2, db_index=True, verbose_name="Kalınlık (mm)")
    description = models.CharField(max_length=255, null=True, blank=True, help_text="Örn: Yarım Panel 0.54x1.08", verbose_name="Açıklama / Ebat (Kritik!)")

    class Meta:
        verbose_name = "2. Variant Mapping"
        verbose_name_plural = "2. Variant Mappings"
        # Aynı malzeme, kalınlık ve ebat tanımından sadece 1 stok çıkmasını garanti eder (Tekil Çözünürlük)

    def __str__(self):
        return f"{self.material_type} - {self.thickness}mm ({self.description}) -> {self.produced_stock.stock_code}"



from django.db import models

class StandardCategory(models.Model):
    """
    Standartları kategorilere ayırmak için opsiyonel model
    İleride ihtiyaç duyarsanız aktif edebilirsiniz
    """
    name = models.CharField(
        max_length=100,
        verbose_name=_("Kategori Adı")
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Açıklama")
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Oluşturulma Tarihi")
    )
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _("Standart Kategorisi")
        verbose_name_plural = _("Standart Kategorileri")
        ordering = ['name']
 
    def __str__(self):
        return self.name
    
    
    

class ReferenceBomHeader(models.Model):
    """
    Step 3: The main record defining the standard, material, and tonnage range.
    Acts as the Header for the BOM matrix.
    """
    category = models.ForeignKey(StandardCategory, on_delete=models.PROTECT, related_name='reference_boms')
    material_type = models.CharField(max_length=100, help_text="e.g., Pre Galvanized-SDG, 304 Stainless")
    
    # Tonnage Range
    min_tonnage = models.IntegerField(verbose_name="Minimum Tonnage",default=0)
    max_tonnage = models.IntegerField(verbose_name="Maximum Tonnage")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "2. Reference BOM Header"
        verbose_name_plural = "2. Reference BOM Headers"
        unique_together = ('category', 'material_type', 'min_tonnage', 'max_tonnage')

    def __str__(self):
        return f"{self.category.name} | {self.min_tonnage}-{self.max_tonnage} Tons ({self.material_type})"


class ReferenceBomLine(models.Model):
    ZONE_CHOICES = [
        ('WALL', 'Side Wall Panel'),
        ('BASE', 'Base Panel'),
        ('ROOF', 'Roof Panel'),
        ('COVER', 'Manhole / Cleaning Cover'),
        ('ACCESSORY', 'Aksesuarlar (Merdiven vb.)'),
        # köebent hesaplamalrı için eklendi.
        ('EXTERNAL_ANGLE', 'Dış Köşebent / Destek'), 
        ('INTERNAL_TIE', 'İç Gergi (Tij)')
    ]

    bom_header = models.ForeignKey(ReferenceBomHeader, on_delete=models.CASCADE, related_name='lines')
    total_module_height = models.DecimalField(max_digits=4, decimal_places=1, verbose_name="Total Tank Height")
    zone_type = models.CharField(max_length=20, choices=ZONE_CHOICES)
    layer_level = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    
    # HİBRİT YAPI KORUNDU
    required_thickness = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Gereken Kalınlık (Paneller İçin)")
    stock_card = models.ForeignKey(StockCard, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Doğrudan Stok Seçimi (Aksesuarlar İçin)")

    class Meta:
        verbose_name = "5. Reference BOM Line"
        verbose_name_plural = "5. Reference BOM Lines"
        ordering = ['total_module_height', 'zone_type', 'layer_level']

    def __str__(self):
        layer_info = f"Layer {self.layer_level}" if self.layer_level else "Standard"
        val = f"{self.required_thickness}mm" if self.required_thickness else self.stock_card.stock_code
        return f"Height: {self.total_module_height} -> {self.get_zone_type_display()} ({layer_info}) : {val}"



