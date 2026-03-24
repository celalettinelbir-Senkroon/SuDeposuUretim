def seed_ekomaxi_matrix():
    # 1. Kategori ve Başlığı Oluştur
    category, _ = StandardCategory.objects.get_or_create(
        name="Ekomaxi Standartları",
        defaults={"description": "Ekomaxi modüler su deposu mühendislik matrisleri"}
    )

    header, _ = ReferenceBomHeader.objects.get_or_create(
        category=category,
        material_type="Pre Galvaniz-SDG",
        standard_name="EKOMAXİ STANDARTI 0-300 Ton",
        defaults={"min_tonnage": 0, "max_tonnage": 300}
    )

    # Test aşamasında scripti tekrar tekrar çalıştırabilmek için eski kayıtları temizleyelim
    ReferenceBomLine.objects.filter(bom_header=header).delete()

    # 2. Görseldeki Matris Verisi (Sözlük Yapısı)
    # Anahtarlar: Toplam Depo Yüksekliği (Sütunlar)
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

    # 3. Döngü ile Objeleri Hazırla
    for total_height, data in matrix_data.items():
        # Sabit Bölgeler (Taban, Tavan, Kapak)
        lines_to_create.extend([
            ReferenceBomLine(bom_header=header, total_tank_height=total_height, zone_type='BASE', layer_level=None, required_thickness=Decimal(data['base'])),
            ReferenceBomLine(bom_header=header, total_tank_height=total_height, zone_type='ROOF', layer_level=None, required_thickness=Decimal(data['roof'])),
            ReferenceBomLine(bom_header=header, total_tank_height=total_height, zone_type='COVER', layer_level=None, required_thickness=Decimal(data['cover'])),
        ])

        # Yan Duvarlar (Katman Katman)
        for layer, thickness in data['walls'].items():
            lines_to_create.append(
                ReferenceBomLine(bom_header=header, total_tank_height=total_height, zone_type='WALL', layer_level=layer, required_thickness=Decimal(thickness))
            )

    # 4. Veritabanına Toplu Yazma (Performans için bulk_create kullanılır)
    with transaction.atomic():
        ReferenceBomLine.objects.bulk_create(lines_to_create)
    
    print(f"Başarılı! {header.standard_name} için toplam {len(lines_to_create)} adet reçete satırı oluşturuldu.")