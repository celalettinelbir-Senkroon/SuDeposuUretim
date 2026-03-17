import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import apiClient from '../api/axiosClient.ts'
import { useTenant } from '../hooks/useTenant.ts'

export type TenantConfig = {
  slug: string
  name: string
  logo: string | null
  primaryColor: string
}

type TenantContextValue = {
  tenant: TenantConfig
  loading: boolean
  error: string | null
  refreshTenant: () => Promise<void>
}

const TenantContext = createContext<TenantContextValue | undefined>(undefined)

type TenantResponse = {
  slug?: string
  name?: string
  logo?: string | null
  primary_color?: string
}

function toTenantConfig(tenantSlug: string, payload?: TenantResponse): TenantConfig {
  return {
    slug: payload?.slug || tenantSlug,
    name: payload?.name || tenantSlug.toUpperCase(),
    logo: payload?.logo || null,
    primaryColor: payload?.primary_color || '#0284c7',
  }
}

export function TenantProvider({ children }: { children: ReactNode }) {
  const tenantSlug = useTenant()
  const [tenant, setTenant] = useState<TenantConfig>(toTenantConfig(tenantSlug))
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refreshTenant = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiClient.get<TenantResponse>('/api/tenant/config/', {
        headers: {
          'X-Tenant-Slug': tenantSlug,
        },
      })

      setTenant(toTenantConfig(tenantSlug, response.data))
    } catch {
      setError('Tenant bilgileri alinamadi.')
      setTenant(toTenantConfig(tenantSlug))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refreshTenant()
  }, [tenantSlug])

  const value = useMemo(
    () => ({ tenant, loading, error, refreshTenant }),
    [tenant, loading, error]
  )

  return <TenantContext.Provider value={value}>{children}</TenantContext.Provider>
}

export function useTenantContext() {
  const context = useContext(TenantContext)
  if (!context) {
    throw new Error('useTenantContext must be used within TenantProvider')
  }

  return context
}
