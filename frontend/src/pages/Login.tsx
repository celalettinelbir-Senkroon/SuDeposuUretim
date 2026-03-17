import { useState, type FormEvent } from 'react'
import { Alert, Avatar, Box, Button, Paper, Stack, TextField, Typography } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { loginWithJwt } from '../auth/sessionAuth.ts'
import { useTenantContext } from '../context/TenantContext.tsx'

function Login() {
  const navigate = useNavigate()
  const {
    tenant: { name, logo, primaryColor },
  } = useTenantContext()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await loginWithJwt({
        username,
        password,
      })

      navigate('/dashboard', { replace: true })
    } catch {
      setError('Giris basarisiz. Bilgilerinizi kontrol edin.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        px: 2,
        background:
          'radial-gradient(circle at top right, rgba(2,132,199,0.12), transparent 45%), linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%)',
      }}
    >
      <Paper sx={{ width: '100%', maxWidth: 420, p: 4, borderTop: `6px solid ${primaryColor}` }}>
        <Stack spacing={2.5}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            {logo ? (
              <Box
                component="img"
                src={logo}
                alt={`${name} logo`}
                sx={{ width: 52, height: 52, objectFit: 'contain', borderRadius: 1 }}
              />
            ) : (
              <Avatar sx={{ width: 52, height: 52, bgcolor: primaryColor }}>
                {name.slice(0, 1)}
              </Avatar>
            )}
            <Box>
              <Typography variant="subtitle2" color="text.secondary">
                Tenant
              </Typography>
              <Typography variant="h6">{name}</Typography>
            </Box>
          </Stack>

          <Typography variant="h5" fontWeight={700}>
            Yonetim Girisi
          </Typography>

          {error ? <Alert severity="error">{error}</Alert> : null}

          <Box component="form" onSubmit={handleSubmit}>
            <Stack spacing={2}>
              <TextField
                label="Kullanici adi"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
                fullWidth
              />
              <TextField
                label="Sifre"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                fullWidth
              />
              <Button type="submit" variant="contained" size="large" disabled={loading}>
                {loading ? 'Giris yapiliyor...' : 'Giris Yap'}
              </Button>
            </Stack>
          </Box>
        </Stack>
      </Paper>
    </Box>
  )
}

export default Login
