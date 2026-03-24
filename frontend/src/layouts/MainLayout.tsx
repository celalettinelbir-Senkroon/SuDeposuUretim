import { useMemo, useState, type MouseEvent, type ReactNode } from 'react'
import {
  AppBar,
  Avatar,
  Badge,
  Box,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
} from '@mui/material'
import DashboardIcon from '@mui/icons-material/Dashboard'
import PeopleAltIcon from '@mui/icons-material/PeopleAlt'
import PrecisionManufacturingIcon from '@mui/icons-material/PrecisionManufacturing'
import Inventory2Icon from '@mui/icons-material/Inventory2'
import SettingsIcon from '@mui/icons-material/Settings'
import QueryStatsIcon from '@mui/icons-material/QueryStats'
import NotificationsNoneIcon from '@mui/icons-material/NotificationsNone'
import MenuIcon from '@mui/icons-material/Menu'
import DarkModeIcon from '@mui/icons-material/DarkMode'
import LightModeIcon from '@mui/icons-material/LightMode'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useTheme } from '@mui/material/styles'
import { logoutJwt } from '../auth/sessionAuth.ts'
import { useTenantContext } from '../context/TenantContext.tsx'

const DRAWER_WIDTH = 280

type MainLayoutProps = {
  mode: 'light' | 'dark'
  onToggleTheme: () => void
  notificationCount?: number
}

type MenuItemType = {
  label: string
  path: string
  icon: ReactNode
}

function MainLayout({ mode, onToggleTheme, notificationCount = 7 }: MainLayoutProps) {
  const theme = useTheme()
  const navigate = useNavigate()
  const isDesktop = useMediaQuery(theme.breakpoints.up('md'))
  const location = useLocation()
  const {
    tenant: { name, logo },
  } = useTenantContext()

  const [mobileOpen, setMobileOpen] = useState(false)
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null)

  const menuItems = useMemo<MenuItemType[]>(
    () => [
      { label: 'Dashboard', path: '/dashboard', icon: <DashboardIcon /> },
      { label: 'Cari Hesaplar', path: '/cari-hesaplar', icon: <PeopleAltIcon /> },
      {
        label: 'Uretim Modulu',
        path: '/uretim-modulu',
        icon: <PrecisionManufacturingIcon />,
      },
      { label: 'Stok Yonetimi', path: '/stok-yonetimi', icon: <Inventory2Icon /> },
      { label: 'Maliyet Analiz', path: '/maliyet-analiz', icon: <QueryStatsIcon /> },
      { label: 'Ayarlar', path: '/ayarlar', icon: <SettingsIcon /> },
    ],
    []
  )

  const isActive = (path: string) => location.pathname === path

  const handleDrawerToggle = () => {
    setMobileOpen((prev) => !prev)
  }

  const handleProfileMenuOpen = (event: MouseEvent<HTMLElement>) => {
    setMenuAnchor(event.currentTarget)
  }

  const handleProfileMenuClose = () => {
    setMenuAnchor(null)
  }

  const handleLogout = async () => {
    await logoutJwt()
    handleProfileMenuClose()
    navigate('/login', { replace: true })
  }

  const drawerContent = (
    <Box sx={{ height: '100%', px: 2, py: 2 }}>
      <Box sx={{ px: 1.5, py: 1, display: 'flex', justifyContent: 'center' }}>
        {logo ? (
          <Box
            component="img"
            src={logo}
            alt={`${name} logo`}
            sx={{ height: 56, width: 'auto', objectFit: 'contain' }}
          />
        ) : (
          <Box
            component="img"
            src="/Normal.png"
            alt="Tenant logo"
            sx={{ height: 56, width: 'auto', objectFit: 'contain' }}
          />
        )}
      </Box>
      <Typography variant="subtitle2" textAlign="center" sx={{ px: 1.5, pb: 1 }}>
        {name}
      </Typography>
      <Divider sx={{ my: 1 }} />

      <List>
        {menuItems.map((item) => {
          const selected = isActive(item.path)

          return (
            <ListItem key={item.path} disablePadding>
              <ListItemButton
                component={Link}
                to={item.path}
                selected={selected}
                onClick={() => {
                  if (!isDesktop) setMobileOpen(false)
                }}
                sx={{
                  '&.Mui-selected': {
                    backgroundColor: theme.palette.primary.main,
                    color: theme.palette.primary.contrastText,
                  },
                  '&.Mui-selected .MuiListItemIcon-root': {
                    color: theme.palette.primary.contrastText,
                  },
                }}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItemButton>
            </ListItem>
          )
        })}
      </List>
    </Box>
  )

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar
        color="inherit"
        position="fixed"
        sx={{
          width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
          ml: { md: `${DRAWER_WIDTH}px` },
          backdropFilter: 'blur(6px)',
          bgcolor: mode === 'light' ? 'rgba(255,255,255,0.85)' : 'rgba(17,28,46,0.85)',
        }}
      >
       <Toolbar>
          {!isDesktop && (
            <IconButton edge="start" onClick={handleDrawerToggle} sx={{ mr: 1 }}>
              <MenuIcon />
            </IconButton>
          )}

          {/* METNİ KALDIRDIK, YERİNE İKONLARI SAĞA İTECEK GÖRÜNMEZ BİR BOŞLUK (SPACER) KOYDUK */}
          <Box sx={{ flexGrow: 1 }} />

          <Tooltip title="Bildirimler">
            <IconButton>
              <Badge badgeContent={notificationCount} color="error">
                <NotificationsNoneIcon />
              </Badge>
            </IconButton>
          </Tooltip>

          <Tooltip title={mode === 'light' ? 'Karanlik moda gec' : 'Aydinlik moda gec'}>
            <IconButton onClick={onToggleTheme}>
              {mode === 'light' ? <DarkModeIcon /> : <LightModeIcon />}
            </IconButton>
          </Tooltip>

          <IconButton onClick={handleProfileMenuOpen} sx={{ ml: 1 }}>
            <Avatar sx={{ width: 34, height: 34 }}>SY</Avatar>
          </IconButton>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', md: 'none' },
            '& .MuiDrawer-paper': {
              width: DRAWER_WIDTH,
              boxSizing: 'border-box',
            },
          }}
        >
          {drawerContent}
        </Drawer>

        <Drawer
          variant="permanent"
          open
          sx={{
            display: { xs: 'none', md: 'block' },
            '& .MuiDrawer-paper': {
              width: DRAWER_WIDTH,
              boxSizing: 'border-box',
            },
          }}
        >
          {drawerContent}
        </Drawer>
      </Box>

      {/* Toolbar boslugu ile icerigin AppBar altinda kalmasini engelliyoruz. */}
      <Box component="main" sx={{ flexGrow: 1, p: { xs: 2, md: 3 } }}>
        <Toolbar />
        <Outlet />
      </Box>

      <Menu anchorEl={menuAnchor} open={Boolean(menuAnchor)} onClose={handleProfileMenuClose}>
        <MenuItem onClick={handleProfileMenuClose}>Profil</MenuItem>
        <MenuItem onClick={handleLogout}>Cikis Yap</MenuItem>
      </Menu>
    </Box>
  )
}

export default MainLayout
