# AGENTCMD - BOM Endpoint Dokumantasyonu

Bu dosya, backend tarafinda bulunan BOM hesaplama endpointlerinin kisa ve net kullanim dokumantasyonudur.

## Base URL

- Lokal: `http://localhost:8000`
- Prefix: `/api/bom/`

## Endpoint Listesi

1. `POST /api/bom/tank/calculate/`
2. `POST /api/bom/tank/warehouse-bom/`
3. `POST /api/bom/depo/hesapla-recete/`

`/tank/warehouse-bom/` ve `/depo/hesapla-recete/` ayni hesaplama motorunu cagirir (alias route).

## 1) Tank Hesaplama

### URL

`POST /api/bom/tank/calculate/`

### Amac

- Girilen depo olculerinden hacim ve tonaj hesaplar.
- Standart + tonaj araligina gore uygun BOM Header bulur.
- Girilen yukseklige en yakin modul yuksekligindeki BOM satirlarini dondurur.

### Request Body

```json
{
	"en": 2,
	"boy": 3,
	"yukseklik": 2,
	"standart": "Ekomaxi Standartlari"
}
```

Alternatif anahtarlar da desteklenir:

- `width` -> `en`
- `length` -> `boy`
- `height` -> `yukseklik`
- `standard` -> `standart`

### Response (200)

```json
{
	"inputs": {
		"en": 2.0,
		"boy": 3.0,
		"yukseklik": 2.0,
		"standart": "Ekomaxi Standartlari"
	},
	"calculation": {
		"volume_m3": 12.0,
		"capacity_ton": 12.0
	},
	"standard_found": true,
	"matched_standard": {
		"id": 1,
		"name": "Ekomaxi Standartlari"
	},
	"matched_header": {
		"id": 10,
		"material_type": "Pre Galvaniz-SDG",
		"tonnage_range": {
			"min": 0,
			"max": 300
		},
		"selected_module_height": 2.0
	},
	"bom_lines": [
		{
			"zone_type": "BASE",
			"layer_level": null,
			"required_thickness": 2.0,
			"stock_code": null
		}
	]
}
```

### Validation Hatalari (400)

- Zorunlu alan eksik: `en`, `boy`, `yukseklik`, `standart`
- Sayisal alan formati gecersiz
- `en`, `boy`, `yukseklik` <= 0

## 2) Depo + Recete + Stok Yeterlilik Hesaplama

### URL

- `POST /api/bom/tank/warehouse-bom/`
- `POST /api/bom/depo/hesapla-recete/`

### Amac

- Tank olculerinden tonaj bulur.
- Uygun recete satirlarini secip satir bazli ihtiyac miktari hesaplar.
- Gonderilen depo stoklari ile yeterli/yetersiz analizini dondurur.

### Request Body

```json
{
	"en": 2,
	"boy": 3,
	"yukseklik": 2,
	"standart": "Ekomaxi Standartlari",
	"malzeme": "SDG",
	"depo_stoklari": [
		{ "stock_code": "SAC-2MM", "qty": 10 },
		{ "stock_code": "SAC-3MM", "qty": 10 }
	]
}
```

Alternatif alanlar:

- `material_type` -> `malzeme`
- `warehouse_stocks` -> `depo_stoklari`
- `quantity` -> `qty`

### Miktar Hesaplama Kurallari

- `BASE` ve `ROOF`: `en x boy` (birim: `m2`)
- `WALL`: `2 x (en + boy) x 0.5` (birim: `m2`)
- Diger zonelar (`COVER`, `ACCESSORY`): `1` (birim: `adet`)

### Response (200)

```json
{
	"inputs": {
		"en": 2.0,
		"boy": 3.0,
		"yukseklik": 2.0,
		"standart": "Ekomaxi Standartlari",
		"malzeme": "SDG"
	},
	"calculation": {
		"volume_m3": 12.0,
		"capacity_ton": 12.0
	},
	"standard_found": true,
	"matched_standard": {
		"id": 1,
		"name": "Ekomaxi Standartlari"
	},
	"matched_header": {
		"id": 10,
		"material_type": "Pre Galvaniz-SDG",
		"tonnage_range": {
			"min": 0,
			"max": 300
		},
		"selected_module_height": 2.0
	},
	"bom_lines": [
		{
			"zone_type": "BASE",
			"layer_level": null,
			"required_thickness": 2.0,
			"required_qty": 6.0,
			"unit": "m2",
			"stock_code": "SAC-2MM",
			"stock_name": "SAC BASE 2MM",
			"available_qty": 10.0,
			"is_sufficient": true
		}
	],
	"warehouse_check": {
		"is_available": true,
		"shortages": []
	}
}
```

### Notlar

- Her zaman HTTP `200` doner, fakat `warehouse_check.is_available` ile stok uygunlugu takip edilir.
- Standart veya header bulunamazsa `matched_header = null` ve `bom_lines = []` doner.
- Uygun stok karti bulunamayan satirlar `shortages` icine reason ile eklenir.

## Hata Senaryolari

- Gecersiz body veya tip hatasi -> `400`
- Zorunlu alan eksigi -> `400`

## Hızlı cURL Ornekleri

### Tank calculate

```bash
curl -X POST "http://localhost:8000/api/bom/tank/calculate/" \
	-H "Content-Type: application/json" \
	-d '{"en":2,"boy":3,"yukseklik":2,"standart":"Ekomaxi Standartlari"}'
```

### Depo recete hesaplama

```bash
curl -X POST "http://localhost:8000/api/bom/depo/hesapla-recete/" \
	-H "Content-Type: application/json" \
	-d '{
		"en":2,
		"boy":3,
		"yukseklik":2,
		"standart":"Ekomaxi Standartlari",
		"malzeme":"SDG",
		"depo_stoklari":[
			{"stock_code":"SAC-2MM","qty":10},
			{"stock_code":"SAC-3MM","qty":10}
		]
	}'
```

## Kod Referanslari

- Endpoint implementasyonu: `bom_engine/views.py`
- Route tanimlari: `bom_engine/urls.py`
- Testler: `bom_engine/tests.py`
