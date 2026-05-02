import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

interface OAuthPolicy {
  id: string
  name: string
  oauth_sub: string[]
  oauth_email: string[]
  oauth_username: string[]
  tools_glob: string[]
  ip_allowlist: string[]
  created_at: string
  created_by: string
  revoked_at: string | null
}

export default function OAuthPolicies() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['oauth_policies'],
    queryFn: () => api<OAuthPolicy[]>('/oauth_policies'),
  })

  if (isLoading) return <div className="text-text-secondary">Loading…</div>
  if (error) return <div className="text-red-500">{(error as Error).message}</div>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">OAuth policies</h1>
      <p className="text-text-secondary text-sm mb-4">
        Keycloak-identity-matched policies. Each entry binds a sub / email /
        username (any one matches) to a tool scope.
      </p>
      <div className="space-y-3">
        {(data ?? []).map((p) => (
          <div key={p.id} className="rounded border border-border p-4 bg-bg-secondary">
            <div className="flex items-baseline gap-3">
              <h2 className="font-semibold">{p.name}</h2>
              <span className="text-xs text-text-secondary">created by {p.created_by}</span>
            </div>
            <dl className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1 text-sm">
              <div className="flex gap-2"><dt className="text-text-secondary w-24">sub</dt><dd className="font-mono text-xs break-all">{p.oauth_sub.join(', ') || '—'}</dd></div>
              <div className="flex gap-2"><dt className="text-text-secondary w-24">email</dt><dd className="font-mono text-xs">{p.oauth_email.join(', ') || '—'}</dd></div>
              <div className="flex gap-2"><dt className="text-text-secondary w-24">username</dt><dd className="font-mono text-xs">{p.oauth_username.join(', ') || '—'}</dd></div>
              <div className="flex gap-2"><dt className="text-text-secondary w-24">IP allow</dt><dd className="font-mono text-xs">{p.ip_allowlist.join(', ') || '—'}</dd></div>
              <div className="flex gap-2 md:col-span-2"><dt className="text-text-secondary w-24">tools</dt><dd className="font-mono text-xs break-all">{p.tools_glob.join(', ')}</dd></div>
            </dl>
          </div>
        ))}
        {(data ?? []).length === 0 && <div className="text-text-secondary">No OAuth policies.</div>}
      </div>
    </div>
  )
}
