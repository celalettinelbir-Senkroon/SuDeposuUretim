import axios from 'axios'
import { getCurrentTenantSlug, DEFAULT_TENANT_SLUG } from '../utils/tenant.ts'

const ACCESS_TOKEN_KEY = 'auth_access_token'
const REFRESH_TOKEN_KEY = 'auth_refresh_token'

const LOGIN_ENDPOINT = import.meta.env.VITE_AUTH_LOGIN_ENDPOINT ?? '/api/auth/login/'
const REFRESH_ENDPOINT = import.meta.env.VITE_AUTH_REFRESH_ENDPOINT ?? '/api/auth/token/refresh/'

const getBaseURL = (): string => {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL

  const hostname = window.location.hostname
  const port = import.meta.env.VITE_API_PORT ?? '8000'
  // const protocol = window.location.protocol

  // Örn: http://ekomaxi.localhost:8000
  return `http://${hostname}:${port}`
}

const apiClient = axios.create({
  baseURL: getBaseURL(),
  headers: {
    'Content-Type': 'application/json',
  },
})

// --- İstek (Request) Interceptor ---
apiClient.interceptors.request.use(
  (config) => {
    const tenantSlug = getCurrentTenantSlug()
    const accessToken = window.localStorage.getItem(ACCESS_TOKEN_KEY)

    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`
    }

    if (tenantSlug !== DEFAULT_TENANT_SLUG) {
      config.headers['X-Tenant-Slug'] = tenantSlug
    }

    return config
  },
  (error) => Promise.reject(error)
)

// --- Cevap (Response) Interceptor ---
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status
    const currentPath = window.location.pathname
    const requestConfig = error.config
    const refreshToken = window.localStorage.getItem(REFRESH_TOKEN_KEY)

    if (
      status === 401 &&
      refreshToken &&
      !requestConfig?._retry &&
      requestConfig?.url !== REFRESH_ENDPOINT &&
      requestConfig?.url !== LOGIN_ENDPOINT
    ) {
      requestConfig._retry = true

      try {
        const refreshClient = axios.create({
          baseURL: getBaseURL(),
          headers: {
            'Content-Type': 'application/json',
          },
        })

        const refreshResponse = await refreshClient.post(REFRESH_ENDPOINT, {
          refresh: refreshToken,
        })
        const newAccessToken = refreshResponse.data?.access

        if (newAccessToken) {
          window.localStorage.setItem(ACCESS_TOKEN_KEY, newAccessToken)
          requestConfig.headers.Authorization = `Bearer ${newAccessToken}`
          return apiClient(requestConfig)
        }
      } catch {
        // Refresh başarısızsa kullanıcı tekrar giriş yapmalı.
      }
    }

    if (status === 401) {
      window.localStorage.removeItem(ACCESS_TOKEN_KEY)
      window.localStorage.removeItem(REFRESH_TOKEN_KEY)

      if (currentPath !== '/login') {
        window.location.href = '/login'
      }
    }

    if (status === 403) {
      console.error('Yetki hatasi (403):', error.response?.data)
    }

    if (status === 404) {
      console.error('Adres bulunamadı (404):', error.config?.url)
    }

    return Promise.reject(error)
  }
)

export default apiClient