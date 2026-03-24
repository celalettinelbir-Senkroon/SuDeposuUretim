import { useState, useMemo } from 'react'
import {
  Paper, Typography, TextField, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Box, Grid, Card,
  CardContent, Chip, Alert,
  Select, MenuItem, InputLabel
} from '@mui/material'
import WarehouseIcon from '@mui/icons-material/Warehouse'

// Tam ürün reçetesi verisi (Formüller düzeltildi ve tamamlandı)
const urunRecetesi = [
  // DUVAR PANELLERİ (oncelik = Kat Sırası)
  {
    grup: "01- Duvar", kategori: "Paneller", altKategori: "1 - Duvar Panelleri",
    kod: "151.2.310025", tanim: "Modül- 1.08x1.08- 2.5 mm",
    birim: "Adet", birimFiyat: 350.00, oncelik: 1,
    formul: "((NEN+NBOYA)*2)-1" // 1. Katta 1 kapak düşülür
  },
  {
    grup: "01- Duvar", kategori: "Paneller", altKategori: "1 - Duvar Panelleri",
    kod: "151.2.320025", tanim: "Modül- 0.54x1.08- 2.5 mm",
    birim: "Adet", birimFiyat: 200.00, oncelik: 1,
    formul: "(YEN*2)+(YBOYA*2)" // Yarım panel varsa karşılıklı 2 duvar için çarpılır
  },
  {
    grup: "01- Duvar", kategori: "Paneller", altKategori: "8 - Kapaklı Duvar Paneli",
    kod: "151.2.330025", tanim: "Kapaklı Modül - 1.08x1.08 2.5 mm",
    birim: "Adet", birimFiyat: 450.00, oncelik: 1,
    formul: "1" // Her depoya 1 adet
  },
  {
    grup: "01- Duvar", kategori: "Paneller", altKategori: "1 - Duvar Panelleri",
    kod: "151.2.310020", tanim: "Modül- 1.08x1.08- 2.0 mm",
    birim: "Adet", birimFiyat: 300.00, oncelik: 2,
    formul: "((NEN+NBOYA)*2)"
  },
  {
    grup: "01- Duvar", kategori: "Paneller", altKategori: "1 - Duvar Panelleri",
    kod: "151.2.320020", tanim: "Modül- 0.54x1.08- 2.0 mm",
    birim: "Adet", birimFiyat: 180.00, oncelik: 2,
    formul: "(YEN*2)+(YBOYA*2)"
  },
  {
    grup: "01- Duvar", kategori: "Paneller", altKategori: "1 - Duvar Panelleri",
    kod: "151.2.310015", tanim: "Modül- 1.08x1.08- 1.5 mm",
    birim: "Adet", birimFiyat: 250.00, oncelik: 3,
    formul: "((NEN+NBOYA)*2)"
  },
  {
    grup: "01- Duvar", kategori: "Paneller", altKategori: "1 - Duvar Panelleri",
    kod: "151.2.320015", tanim: "Modül- 0.54x1.08- 1.5 mm",
    birim: "Adet", birimFiyat: 150.00, oncelik: 3,
    formul: "(YEN*2)+(YBOYA*2)"
  },

  // TABAN PANELLERİ (Alan Hesabı Formülleri Eklendi)
  {
    grup: "05- 1x1 Düz Taban", kategori: "Paneller", altKategori: "2 - Düz Taban Panlleri",
    kod: "151.2.140017", tanim: "Taban Sacı- 1.08x1.08 - 1.7 mm",
    birim: "Adet", birimFiyat: 380.00, oncelik: 0,
    formul: "NEN * NBOYA" // İç Alan Tam Panel
  },
  {
    grup: "09- 0.5x1 Düz Taban", kategori: "Paneller", altKategori: "2 - Düz Taban Panlleri",
    kod: "151.2.150017", tanim: "Taban Sacı- 0.54x1.08 - 1.7 mm",
    birim: "Adet", birimFiyat: 220.00, oncelik: 0,
    formul: "(NEN * YBOYA) + (NBOYA * YEN)" // Kenar Şeritler
  },
  {
    grup: "27- Çeyrek Bombeli Taban", kategori: "Paneller", altKategori: "3 - Bombeli Taban Panelleri",
    kod: "151.2.541017", tanim: "Taban Modül- 0.54x0.54- 1.7 mm",
    birim: "Adet", birimFiyat: 180.00, oncelik: 0,
    formul: "YEN * YBOYA" // Sadece En ve Boy buçukluysa 1 adet köşeye çıkar
  },

  // TAVAN PANELLERİ
  {
    grup: "03- 1x1 Düz Tavan", kategori: "Paneller", altKategori: "4 - Tavan Panelleri",
    kod: "151.2.220007", tanim: "Tavan Sacı- 1.08x1.08- 0.8 mm",
    birim: "Adet", birimFiyat: 240.00, oncelik: 0,
    formul: "NEN * NBOYA"
  },
  {
    grup: "08- 0.5x1 Düz Tavan", kategori: "Paneller", altKategori: "4 - Tavan Panelleri",
    kod: "151.2.230007", tanim: "Tavan Sacı- 0.54x1.08- 0.8 mm",
    birim: "Adet", birimFiyat: 150.00, oncelik: 0,
    formul: "(NEN * YBOYA) + (NBOYA * YEN)"
  },

  // AKSESUAR VE SARF MALZEMELERİ (Şimdilik Sabit Formüller)
  {
    grup: "29- Sarf ve Aksesuarlar", kategori: "Sızdırmazlık", altKategori: "21",
    kod: "150.1.250002", tanim: "Silikon",
    birim: "Adet", birimFiyat: 35.00, oncelik: 0,
    formul: "Math.ceil(((NEN+NBOYA)*2*YUKSEKLIK) * 0.5)" // Çevre * Yükseklik * Çarpan (Örnek)
  }
];

function MaliyetAnalizCard() {
  const [depoBoyutlari, setDepoBoyutlari] = useState({
    en: 0,
    boy: 0,
    yukseklik: 0,
  });

  const modulSayilari = useMemo(() => {
    const { en, boy, yukseklik } = depoBoyutlari;

    // NEN ve NBOYA: Tam panel (1m) sayıları
    const NEN = Math.floor(en);
    const NBOYA = Math.floor(boy);

    // YEN ve YBOYA: Buçuklu modül VAR MI YOK MU bayrakları (1 veya 0)
    // Örn: 2.5 ise kalanı 0 değildir, yani YEN = 1 olur.
    const YEN = en % 1 !== 0 ? 1 : 0;
    const YBOYA = boy % 1 !== 0 ? 1 : 0;

    const YUKSEKLIK = Math.floor(yukseklik); // Güvenlik için

    return { NEN, NBOYA, YEN, YBOYA, YUKSEKLIK };
  }, [depoBoyutlari]);

  const formulHesapla = (formul) => {
    if (!formul || formul.trim() === '') return 0;

    try {
      const { NEN, NBOYA, YEN, YBOYA, YUKSEKLIK } = modulSayilari;

      // eval() yerine daha güvenli ve hızlı Function kullanımı
      // Formül içindeki değişkenleri doğrudan parametre olarak iletiyoruz
      const hesaplayici = new Function('NEN', 'NBOYA', 'YEN', 'YBOYA', 'YUKSEKLIK', `return ${formul}`);

      const sonuc = hesaplayici(NEN, NBOYA, YEN, YBOYA, YUKSEKLIK);
      return Math.max(0, Math.ceil(sonuc)); // Negatif sayı çıkmasını engeller
    } catch (error) {
      console.error('Formül hesaplama hatası:', error);
      return 0;
    }
  };

  const hesaplanmisMalzemeler = useMemo(() => {
    // Ölçüler 0 ise boş liste dön
    if (depoBoyutlari.en <= 0 || depoBoyutlari.boy <= 0 || depoBoyutlari.yukseklik <= 0) {
      return [];
    }

    return urunRecetesi
      .map(urun => {
        let miktar = 0;

        // 1. KURAL: Duvar paneli ise (oncelik > 0), deponun yüksekliğini aşan katları EKLEME!
        const isDuvarPaneli = urun.oncelik > 0;

        if (isDuvarPaneli) {
          if (urun.oncelik <= depoBoyutlari.yukseklik) {
            miktar = formulHesapla(urun.formul);
          }
        }
        // 2. KURAL: Taban, Tavan ve Aksesuar ise (oncelik = 0) formülü direkt çalıştır
        else {
          miktar = formulHesapla(urun.formul);
        }

        const tutar = miktar * urun.birimFiyat;

        return { ...urun, miktar, tutar };
      })
      .filter(urun => urun.miktar > 0); // Sadece miktarı 0'dan büyükleri sepete at
  }, [modulSayilari, depoBoyutlari.yukseklik]);

  const toplamMaliyet = useMemo(() => {
    return hesaplanmisMalzemeler.reduce((toplam, urun) => toplam + urun.tutar, 0);
  }, [hesaplanmisMalzemeler]);

  const handleBoyutDegisiklik = (alan, deger) => {
    setDepoBoyutlari(prev => ({
      ...prev,
      [alan]: parseFloat(deger) || 0
    }));
  };

  return (
    <Paper sx={{ p: 3 }}>




      <Card sx={{ mb: 3, bgcolor: '#f8f9fa' }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Depo Boyutları (Metre)
          </Typography>
          <Grid container spacing={3}>

            <Grid item xs={12}>
              <Select
                fullWidth
                labelId="depo-standartlari-label"
                id="depo-standartlari-select"
                label="Depo Standartları"
                onChange={(e) => handleBoyutDegisiklik('depoStandarti', e.target.value)}
              >
                <MenuItem value="pre_galvaniz">Pre Galvaniz</MenuItem>
                <MenuItem value="sdg">SDG (Sıcak Daldırma Galvaniz)</MenuItem>
                <MenuItem value="aisi304">AISI304</MenuItem>
                <MenuItem value="aisi316">AISI316</MenuItem>
              </Select>
            </Grid>

            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="En (metre)"
                type="number"
                value={depoBoyutlari.en || ''}
                onChange={(e) => handleBoyutDegisiklik('en', e.target.value)}
                inputProps={{ step: 0.5, min: 0 }}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Boy (metre)"
                type="number"
                value={depoBoyutlari.boy || ''}
                onChange={(e) => handleBoyutDegisiklik('boy', e.target.value)}
                inputProps={{ step: 0.5, min: 0 }}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Yükseklik (Kat)"
                type="number"
                value={depoBoyutlari.yukseklik || ''}
                onChange={(e) => handleBoyutDegisiklik('yukseklik', e.target.value)}
                inputProps={{ step: 1, min: 0 }}
              />
            </Grid>



          </Grid>
        </CardContent>
      </Card>



      {hesaplanmisMalzemeler.length === 0 ? (
        <Alert severity="warning">
          Lütfen En, Boy ve Yükseklik değerlerinin tümünü giriniz. (Örn: 2, 3, 2)
        </Alert>
      ) : (
        <>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ bgcolor: 'grey.100' }}>
                  <TableCell><strong>Grup</strong></TableCell>
                  <TableCell><strong>Ürün Kodu</strong></TableCell>
                  <TableCell><strong>Tanım</strong></TableCell>
                  <TableCell align="center"><strong>Miktar</strong></TableCell>
                  <TableCell align="center"><strong>Birim</strong></TableCell>
                  <TableCell align="right"><strong>Tutar</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {hesaplanmisMalzemeler.map((urun, idx) => (
                  <TableRow key={idx} hover>
                    <TableCell><Typography variant="body2">{urun.grup}</Typography></TableCell>
                    <TableCell><Typography variant="body2" sx={{ fontFamily: 'monospace' }}>{urun.kod}</Typography></TableCell>
                    <TableCell>{urun.tanim}</TableCell>
                    <TableCell align="center">
                      <Chip label={urun.miktar} size="small" color="primary" variant="outlined" />
                    </TableCell>
                    <TableCell align="center">{urun.birim}</TableCell>
                    <TableCell align="right">
                      <strong>₺{urun.tutar.toLocaleString('tr-TR', { minimumFractionDigits: 2 })}</strong>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}
    </Paper>
  );
}

export default MaliyetAnalizCard;