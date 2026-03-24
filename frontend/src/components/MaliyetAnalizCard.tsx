import { useEffect, useMemo, useState } from 'react'
import {
  Paper, Typography, TextField, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Grid, Card,
  CardContent, Alert, CircularProgress,
  Select, MenuItem, InputLabel, FormControl
} from '@mui/material'
import apiClient from '../api/axiosClient'

type DepoFormu = {
  en: number
  boy: number
  yukseklik: number
  depoStandarti: string
  depoTipi: string
}

type BomLine = {
  zone_type?: string
  layer_level?: number | null
  required_thickness?: number | null
  required_qty?: number | null
  unit?: string | null
  stock_code?: string | null
  stock_name?: string | null
  available_qty?: number | null
  is_sufficient?: boolean | null
}

type BomResponse = {
  calculation?: {
    volume_m3?: number
    capacity_ton?: number
  }
  bom_lines?: BomLine[]
}

function MaliyetAnalizCard() {
  const [depoBoyutlari, setDepoBoyutlari] = useState<DepoFormu>({
    en: 0,
    boy: 0,
    yukseklik: 0,
    depoStandarti: '',
    depoTipi: '',
  });
  const [isCalculating, setIsCalculating] = useState(false)
  const [apiError, setApiError] = useState('')
  const [bomData, setBomData] = useState<BomResponse | null>(null)

  const formHazir = useMemo(() => {
    return (
      depoBoyutlari.en > 0 &&
      depoBoyutlari.boy > 0 &&
      depoBoyutlari.yukseklik > 0 &&
      depoBoyutlari.depoStandarti !== '' &&
      depoBoyutlari.depoTipi !== ''
    )
  }, [depoBoyutlari])

  useEffect(() => {
    if (!formHazir) {
      setBomData(null)
      setApiError('')
      return
    }

    const timer = setTimeout(async () => {
      setIsCalculating(true)
      setApiError('')

      try {
        const response = await apiClient.post('/api/bom/depo/hesapla-recete/', {
          en: depoBoyutlari.en,
          boy: depoBoyutlari.boy,
          yukseklik: depoBoyutlari.yukseklik,
          standart: depoBoyutlari.depoStandarti,
          malzeme: depoBoyutlari.depoTipi,
          depo_stoklari: [],
        })

        setBomData(response.data as BomResponse)
      } catch (error) {
        console.error('Recete hesaplama hatasi:', error)
        setBomData(null)
        setApiError('Hesaplama servisine ulasilamadi. Lütfen tekrar deneyin.')
      } finally {
        setIsCalculating(false)
      }
    }, 350)

    return () => {
      clearTimeout(timer)
    }
  }, [formHazir, depoBoyutlari])

  const bomSatirlari = bomData?.bom_lines ?? []

  const handleBoyutDegisiklik = (
    alan: 'en' | 'boy' | 'yukseklik' | 'depoStandarti' | 'depoTipi',
    deger: string
  ) => {
    const yeniDeger = alan === 'en' || alan === 'boy' || alan === 'yukseklik'
      ? parseFloat(deger) || 0
      : deger;

    setDepoBoyutlari((prev) => ({
      ...prev,
      [alan]: yeniDeger
    }))
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Card sx={{ mb: 3, bgcolor: '#f8f9fa' }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Depo Boyutları (Metre)
          </Typography>
          <Grid container spacing={2} columns={{ xs: 12, md: 15 }}>

            <Grid size={{ xs: 12, md: 3 }}>
              <FormControl fullWidth>
                <InputLabel id="depo-standartlari-label">Standart</InputLabel>
                <Select
                  labelId="depo-standartlari-label"
                  id="depo-standartlari-select"
                  label="Standart"
                  value={depoBoyutlari.depoStandarti}
                  onChange={(e) => handleBoyutDegisiklik('depoStandarti', e.target.value)}
                >
                  <MenuItem value="Ekomaxi Standartlari">Ekomaxi Standartları</MenuItem>
                
                </Select>
              </FormControl>
            </Grid>

            <Grid size={{ xs: 12, md: 3 }}>
              <FormControl fullWidth>
                <InputLabel id="depo-tipi-label">Tür</InputLabel>
                <Select
                  labelId="depo-tipi-label"
                  id="depo-tipi-select"
                  label="Tür"
                  value={depoBoyutlari.depoTipi}
                  onChange={(e) => handleBoyutDegisiklik('depoTipi', e.target.value)}
                >
                  <MenuItem value="Pre Galvaniz">Pre Galvaniz</MenuItem>
                  <MenuItem value="SDG">SDG</MenuItem>
                  <MenuItem value="AISI304">AISI304</MenuItem>
                  <MenuItem value="AISI316">AISI316</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                fullWidth
                label="En (metre)"
                type="number"
                value={depoBoyutlari.en || ''}
                onChange={(e) => handleBoyutDegisiklik('en', e.target.value)}
                inputProps={{ step: 0.5, min: 0 }}
              />
            </Grid>

            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                fullWidth
                label="Boy (metre)"
                type="number"
                value={depoBoyutlari.boy || ''}
                onChange={(e) => handleBoyutDegisiklik('boy', e.target.value)}
                inputProps={{ step: 0.5, min: 0 }}
              />
            </Grid>

            <Grid size={{ xs: 12, md: 3 }}>
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

      {isCalculating && (
        <Alert icon={<CircularProgress size={18} />} severity="info" sx={{ mb: 2 }}>
          Reçete hesaplanıyor...
        </Alert>
      )}

      {apiError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {apiError}
        </Alert>
      )}

      {!formHazir ? (
        <Alert severity="warning">
          Lütfen Standart, Tür, En, Boy ve Yükseklik alanlarını doldurunuz.
        </Alert>
      ) : bomSatirlari.length === 0 ? (
        <Alert severity="info">
          Hesaplama sonucu reçete satırı bulunamadı.
        </Alert>
      ) : (
        <>
          <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
            Hacim: {bomData?.calculation?.volume_m3 ?? 0} m3 | Tonaj: {bomData?.calculation?.capacity_ton ?? 0} ton
          </Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ bgcolor: 'grey.100' }}>
                  <TableCell><strong>Bölge</strong></TableCell>
                  <TableCell align="center"><strong>Katman</strong></TableCell>
                  <TableCell align="center"><strong>Kalınlık</strong></TableCell>
                  <TableCell align="center"><strong>Gerekli Miktar</strong></TableCell>
                  <TableCell align="center"><strong>Birim</strong></TableCell>
                  <TableCell><strong>Stok Kodu</strong></TableCell>
                  <TableCell><strong>Stok Adı</strong></TableCell>
                  <TableCell align="center"><strong>Durum</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {bomSatirlari.map((satir, idx) => (
                  <TableRow key={idx} hover>
                    <TableCell>{satir.zone_type ?? '-'}</TableCell>
                    <TableCell align="center">{satir.layer_level ?? '-'}</TableCell>
                    <TableCell align="center">{satir.required_thickness ?? '-'}</TableCell>
                    <TableCell align="center">{satir.required_qty ?? '-'}</TableCell>
                    <TableCell align="center">{satir.unit ?? '-'}</TableCell>
                    <TableCell>{satir.stock_code ?? '-'}</TableCell>
                    <TableCell>{satir.stock_name ?? '-'}</TableCell>
                    <TableCell align="center">{satir.is_sufficient === false ? 'Yetersiz' : 'Uygun'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}
    </Paper>
  )
}

export default MaliyetAnalizCard;