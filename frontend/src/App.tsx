import { useMemo, useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { CssBaseline, Paper, Typography } from '@mui/material'
import { ThemeProvider } from '@mui/material/styles'
import ProtectedRoute from './components/ProtectedRoute.tsx'
import { TenantProvider, useTenantContext } from './context/TenantContext.tsx'
import MainLayout from './layouts/MainLayout.tsx'
import Login from './pages/Login.tsx'
import { createAppTheme, type TenantThemeConfig } from './theme.ts'

type ColorMode = 'light' | 'dark'

type PageCardProps = {
  title: string
  description: string
}

function PageCard({ title, description }: PageCardProps) {
  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        {title}
      </Typography>
      <Typography color="text.secondary">{description}</Typography>
    </Paper>
  )
}

function DashboardPage() {
  return (
    <PageCard
      title="Dashboard"
      description="Genel KPI ve operasyonel ozet metriklerinizi bu alanda gorebilirsiniz."
    />
  )
}

function CariHesaplarPage() {
  return (
    <PageCard
      title="Cari Hesaplar"
      description="Musteri ve tedarikci hesap hareketlerini bu modulde yonetin."
    />
  )
}

function UretimModuluPage() {
  return (
    <PageCard
      title="Uretim Modulu"
      description="Uretim emirleri, istasyon takibi ve kapasite planlamasi burada yer alir."
    />
  )
}

function StokYonetimiPage() {
  return (
    <PageCard
      title="Stok Yonetimi"
      description="Depo bazli stok seviyeleri ve kritik esik alarmlari bu ekranda takip edilir."
    />
  )
}

function AyarlarPage() {
  return (
    <PageCard
      title="Ayarlar"
      description="Firma ve tenant bazli sistem ayarlarinizi bu ekrandan yonetebilirsiniz."
    />
  )
}

function App() {
  return (
    <TenantProvider>
      <AppShell />
    </TenantProvider>
  )
}

function AppShell() {
  const [mode, setMode] = useState<ColorMode>('light')
  const { tenant } = useTenantContext()

  const tenantConfig: TenantThemeConfig = {
    primaryColor: tenant.primaryColor,
  }

  const theme = useMemo(() => createAppTheme(mode, tenantConfig), [mode, tenant.primaryColor])

  const handleToggleTheme = () => {
    setMode((prev) => (prev === 'light' ? 'dark' : 'light'))
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route element={<ProtectedRoute />}>
            <Route
              path="/"
              element={<MainLayout mode={mode} onToggleTheme={handleToggleTheme} />}
            >
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="cari-hesaplar" element={<CariHesaplarPage />} />
              <Route path="uretim-modulu" element={<UretimModuluPage />} />
              <Route path="stok-yonetimi" element={<StokYonetimiPage />} />
              <Route path="ayarlar" element={<AyarlarPage />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App