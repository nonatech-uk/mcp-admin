async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const init: RequestInit = {
    method,
    credentials: 'include',
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  }
  const r = await fetch(`/api/v1${path}`, init)
  if (r.status === 401) {
    window.location.href = `/auth/login?next=${encodeURIComponent(window.location.pathname)}`
    throw new Error('redirecting to login')
  }
  if (!r.ok) {
    let detail = `${r.status} ${r.statusText}`
    try {
      const j = await r.json()
      if (j?.detail) detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch { /* not json */ }
    throw new Error(detail)
  }
  return (await r.json()) as T
}

export const api = <T>(path: string) => request<T>('GET', path)
export const apiPost = <T>(path: string, body?: unknown) => request<T>('POST', path, body)
export const apiPatch = <T>(path: string, body: unknown) => request<T>('PATCH', path, body)
export const apiDelete = <T>(path: string) => request<T>('DELETE', path)
