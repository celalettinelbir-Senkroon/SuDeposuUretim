import { useMemo } from 'react'
import { getCurrentTenantSlug } from '../utils/tenant.ts'

export function useTenant() {
  return useMemo(() => getCurrentTenantSlug(), [])
}
