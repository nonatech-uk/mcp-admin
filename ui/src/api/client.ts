export async function api<T>(path: string): Promise<T> {
  const r = await fetch(`/api/v1${path}`, { credentials: 'include' })
  if (r.status === 401) {
    window.location.href = `/auth/login?next=${encodeURIComponent(window.location.pathname)}`
    throw new Error('redirecting to login')
  }
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return (await r.json()) as T
}
