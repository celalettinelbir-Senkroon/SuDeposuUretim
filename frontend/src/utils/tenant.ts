const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1'])

export const DEFAULT_TENANT_SLUG = 'public'

export function extractTenantSlug(hostname: string): string {
  const normalized = hostname.trim().toLowerCase()

  if (!normalized || LOCAL_HOSTS.has(normalized)) {
    return DEFAULT_TENANT_SLUG
  }

  if (normalized.endsWith('.localhost')) {
    const [subdomain] = normalized.split('.')
    return subdomain || DEFAULT_TENANT_SLUG
  }

  const parts = normalized.split('.')
  if (parts.length >= 3) {
    return parts[0] || DEFAULT_TENANT_SLUG
  }

  return DEFAULT_TENANT_SLUG
}

export function getCurrentTenantSlug(): string {
  if (typeof window === 'undefined') {
    return DEFAULT_TENANT_SLUG
  }

  return extractTenantSlug(window.location.hostname)
}
