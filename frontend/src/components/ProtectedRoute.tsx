import { useEffect, useState } from 'react'
import { Box, CircularProgress } from '@mui/material'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { checkJwtAuthenticated } from '../auth/sessionAuth.ts'

function ProtectedRoute() {
  const location = useLocation()
  const [isLoading, setIsLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    let isMounted = true

    const checkAuth = async () => {
      const authenticated = await checkJwtAuthenticated()

      if (!isMounted) return

      setIsAuthenticated(authenticated)
      setIsLoading(false)
    }

    void checkAuth()

    return () => {
      isMounted = false
    }
  }, [location.pathname])

  if (isLoading) {
    return (
      <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
        <CircularProgress size={28} />
      </Box>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <Outlet />
}

export default ProtectedRoute
