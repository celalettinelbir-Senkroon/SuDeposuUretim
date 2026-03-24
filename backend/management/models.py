# from django.db import models
# import uuid
# from django.utils.timezone import now

# # SEÇENEKLER (CHOICES) - Gelecekte buraya ekleme yapabilirsin
# MATERIAL_CHOICES = [
#     ('AISI304', 'Paslanmaz AISI 304'),
#     ('AISI316', 'Paslanmaz AISI 316'),
#     ('SDG', 'Sıcak Daldırma Galvaniz'),
#     ('PREGALVANIZ', 'Pre-Galvaniz'),
# ]

# TANK_STANDARDS = [
#     ('EKOMAXI', 'Ekomaxi Standart'),
#     ('CEVRE_SEHIRCILIK', 'Çevre Şehircilik Standartı'),
# ]

# BASE_TYPES = [
#     ('DUZ', 'Düz Taban'),
#     ('BOMBELI', 'Bombeli Taban'),
# ]

# class StokKarti(models.Model):
#     """
#     Mikro STOKLAR tablosunun Django tarafındaki kapsamlı karşılığı.
#     """
#     # Mikro Temel Alanları
#     sto_Guid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
#     sto_kod = models.CharField(max_length=100, primary_key=True, verbose_name="Stok Kodu")
#     sto_isim = models.CharField(max_length=255, verbose_name="Stok Adı")
#     sto_birim1_ad = models.CharField(max_length=20, default="Adet")
    
#     # Mühendislik / BOM Parametreleri (Mikro Special alanlarından beslenecek)
#     bom_kategori = models.CharField(max_length=100, null=True, blank=True, db_index=True, 
#                                     help_text="Duvar Paneli, Taban Sacı, Civata, Conta vb.")
#     bom_malzeme = models.CharField(max_length=50, choices=MATERIAL_CHOICES, null=True, blank=True)
#     bom_kalinlik_mm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
#     bom_ebat = models.CharField(max_length=50, null=True, blank=True, help_text="Örn: 1x1, 0.5x1, 1x2")
    
#     # Muhasebe ve Depo (Opsiyonel ama Mikro entegrasyonunda lazım olur)
#     sto_muh_kod = models.CharField(max_length=50, default="153")
#     sto_pasif_fl = models.BooleanField(default=False)
#     mikro_id = models.IntegerField(null=True, blank=True, unique=True, verbose_name="Mikro ID")

#     class Meta:
#         verbose_name = "Stok Kartı"
#         verbose_name_plural = "1. Stok Kartları"

#     def __str__(self):
#         return f"{self.sto_kod} | {self.sto_isim}"


# class ReceteAna(models.Model):
#     """
#     Üretilecek olan su deposunun 'Konfigürasyonu'. 
#     Bir sipariş geldiğinde 'Nasıl bir depo?' sorusunun cevabı burada saklanır.
#     """
#     rec_Guid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
#     rec_anakod = models.ForeignKey(StokKarti, on_delete=models.CASCADE, verbose_name="Ana Mamul")
    
#     # Depo Boyutları
#     en = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="En (m)")
#     boy = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Boy (m)")
#     yukseklik = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Yükseklik (m)")
    
#     # Konfigürasyon Varyantları
#     malzeme = models.CharField(max_length=50, choices=MATERIAL_CHOICES, default='AISI304')
#     standart = models.CharField(max_length=50, choices=TANK_STANDARDS, default='EKOMAXI')
#     taban_tipi = models.CharField(max_length=50, choices=BASE_TYPES, default='DUZ')
    
#     # Metadata
#     olusturan_user = models.CharField(max_length=100, null=True, blank=True)
#     olusturma_tarihi = models.DateTimeField(default=now)
#     is_active = models.BooleanField(default=True)

#     class Meta:
#         verbose_name = "Reçete Ana (Depo Yapılandırması)"
#         verbose_name_plural = "2. Reçete Başlıkları"

#     def __str__(self):
#         return f"{self.rec_anakod.sto_kod} - {self.en}x{self.boy}x{self.yukseklik}"


# class ReceteSatir(models.Model):
#     """
#     Hesaplama motoru çalıştıktan sonra çıkan 'Kesinleşmiş' parça listesi.
#     Mikro'daki RECETELER tablosuna 1:1 aktarılacak olan tablo.
#     """
#     recete_ana = models.ForeignKey(ReceteAna, on_delete=models.CASCADE, related_name='satirlar')
#     rec_satirno = models.IntegerField(verbose_name="Satır No")
    
#     # Tüketilen Malzeme
#     rec_tuketim_kod = models.ForeignKey(StokKarti, on_delete=models.PROTECT, verbose_name="Kullanılan Parça")
#     rec_tuketim_miktar = models.DecimalField(max_digits=12, decimal_places=3, verbose_name="Miktar")
#     rec_tuketim_birim = models.CharField(max_length=20, default="Adet")
    
#     # İzlenebilirlik (Hangi aşamada eklendiğini bilmek için)
#     not_alani = models.CharField(max_length=255, null=True, blank=True, help_text="Örn: 1. Kat Duvar Paneli")
#     aktarildi_mi = models.BooleanField(default=False, verbose_name="Mikro'ya Aktarıldı")
    
#     is_active = models.BooleanField(default=True)

#     class Meta:
#         verbose_name = "Reçete Satırı (BOM Line)"
#         verbose_name_plural = "3. Reçete Detay Satırları"
#         ordering = ['rec_satirno']

#     def __str__(self):
#         return f"{self.recete_ana} -> {self.rec_tuketim_kod.sto_kod}"