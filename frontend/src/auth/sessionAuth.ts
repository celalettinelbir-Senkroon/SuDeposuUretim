import apiClient from '../api/axiosClient.ts'

const LOGIN_ENDPOINT = import.meta.env.VITE_AUTH_LOGIN_ENDPOINT ?? '/api/auth/login/'
const REFRESH_ENDPOINT = import.meta.env.VITE_AUTH_REFRESH_ENDPOINT ?? '/api/auth/token/refresh/'
const LOGOUT_ENDPOINT = import.meta.env.VITE_AUTH_LOGOUT_ENDPOINT ?? '/api/auth/logout/'
const ME_ENDPOINT = import.meta.env.VITE_AUTH_ME_ENDPOINT ?? '/api/auth/me/'

const ACCESS_TOKEN_KEY = 'auth_access_token'
const REFRESH_TOKEN_KEY = 'auth_refresh_token'

type LoginPayload = {
  username: string
  password: string
}

type TokenPair = {
  access: string
  refresh: string
}

function saveTokens(tokens: TokenPair): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access)
  window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh)
}

function clearTokens(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY)
  window.localStorage.removeItem(REFRESH_TOKEN_KEY)
}

function extractTokens(data: unknown): TokenPair | null {
  if (!data || typeof data !== 'object') return null

  const payload = data as Record<string, unknown>
  const access =
    typeof payload.access === 'string'
      ? payload.access
      : typeof payload.accessToken === 'string'
        ? payload.accessToken
        : null

  const refresh =
    typeof payload.refresh === 'string'
      ? payload.refresh
      : typeof payload.refreshToken === 'string'
        ? payload.refreshToken
        : null

  if (!access || !refresh) {
    return null
  }

  return { access, refresh }
}

export async function loginWithJwt(payload: LoginPayload): Promise<void> {
  const response = await apiClient.post(LOGIN_ENDPOINT, payload)
  const tokens = extractTokens(response.data)

  if (!tokens) {
    throw new Error('Login response does not contain JWT tokens.')
  }

  saveTokens(tokens)
}

export async function logoutJwt(): Promise<void> {
  const refreshToken = window.localStorage.getItem(REFRESH_TOKEN_KEY)

  try {
    if (refreshToken) {
      await apiClient.post(LOGOUT_ENDPOINT, { refresh: refreshToken })
    } else {
      await apiClient.post(LOGOUT_ENDPOINT)
    }
  } finally {
    clearTokens()
  }
}

export async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = window.localStorage.getItem(REFRESH_TOKEN_KEY)
  if (!refreshToken) return false

  try {
    const response = await apiClient.post(REFRESH_ENDPOINT, { refresh: refreshToken })
    const nextAccess = response.data?.access

    if (!nextAccess || typeof nextAccess !== 'string') {
      clearTokens()
      return false
    }

    window.localStorage.setItem(ACCESS_TOKEN_KEY, nextAccess)
    return true
  } catch {
    clearTokens()
    return false
  }
}

export function hasAccessToken(): boolean {
  return Boolean(window.localStorage.getItem(ACCESS_TOKEN_KEY))
}

export async function checkJwtAuthenticated(): Promise<boolean> {
  if (!hasAccessToken()) {
    return false
  }

  try {
    await apiClient.get(ME_ENDPOINT)
    return true
  } catch {
    return refreshAccessToken()
  }
}
