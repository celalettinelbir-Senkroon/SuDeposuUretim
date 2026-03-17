import { createTheme } from '@mui/material/styles'

type ColorMode = 'light' | 'dark'

export type TenantThemeConfig = {
  primaryColor?: string
  secondaryColor?: string
  backgroundDefault?: string
  backgroundPaper?: string
  textPrimary?: string
  textSecondary?: string
}

// Multi-tenant senaryoda tenant bazli renkleri disaridan override edebilmek icin fonksiyonel tema.
export const createAppTheme = (
  mode: ColorMode = 'light',
  tenantConfig: TenantThemeConfig = {}
) => {
  const palette = {
    light: {
      primary: '#f6861f',
      secondary: '#0f766e',
      backgroundDefault: '#f4f8fb',
      backgroundPaper: '#ffffff',
      textPrimary: '#0f172a',
      textSecondary: '#475569',
    },
    dark: {
      primary: '#f6861f',
      secondary: '#2dd4bf',
      backgroundDefault: '#0b1220',
      backgroundPaper: '#111c2e',
      textPrimary: '#e2e8f0',
      textSecondary: '#94a3b8',
    },
  } as const

  const current = palette[mode]

  return createTheme({
    palette: {
      mode,
      primary: { main: tenantConfig.primaryColor || current.primary },
      secondary: { main: tenantConfig.secondaryColor || current.secondary },
      background: {
        default: tenantConfig.backgroundDefault || current.backgroundDefault,
        paper: tenantConfig.backgroundPaper || current.backgroundPaper,
      },
      text: {
        primary: tenantConfig.textPrimary || current.textPrimary,
        secondary: tenantConfig.textSecondary || current.textSecondary,
      },
    },
    shape: {
      borderRadius: 12,
    },
    typography: {
      fontFamily: "'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif",
      h6: {
        fontWeight: 700,
      },
    },
    components: {
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
          },
        },
      },
      MuiListItemButton: {
        styleOverrides: {
          root: {
            borderRadius: 10,
            marginBottom: 4,
          },
        },
      },
      MuiAppBar: {
        defaultProps: {
          elevation: 0,
        },
      },
    },
  })
}
