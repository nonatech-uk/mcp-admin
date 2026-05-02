import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

interface Token {
  id: string
  name: string
  token_preview: string
  tools_glob: string[]
  ip_allowlist: string[]
  created_at: string
  created_by: string
  last_used_at: string | null
  revoked_at: string | null
}

export default function Tokens() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['tokens'],
    queryFn: () => api<Token[]>('/tokens'),
  })

  if (isLoading) return <div className="text-text-secondary">Loading…</div>
  if (error) return <div className="text-red-500">{(error as Error).message}</div>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Static tokens</h1>
      <p className="text-text-secondary text-sm mb-4">
        Bearer tokens for non-claude.ai callers. Phase 1 is read-only —
        creating / rotating / revoking comes in Phase 2.
      </p>
      <div className="overflow-x-auto rounded border border-border">
        <table className="w-full text-sm">
          <thead className="bg-bg-secondary text-text-secondary">
            <tr>
              <th className="text-left px-3 py-2">Name</th>
              <th className="text-left px-3 py-2">Preview</th>
              <th className="text-left px-3 py-2">Tools</th>
              <th className="text-left px-3 py-2">IP allowlist</th>
              <th className="text-left px-3 py-2">Last used</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((t) => (
              <tr key={t.id} className="border-t border-border">
                <td className="px-3 py-2 font-medium">{t.name}</td>
                <td className="px-3 py-2 font-mono text-xs">{t.token_preview}…</td>
                <td className="px-3 py-2 font-mono text-xs">{t.tools_glob.join(', ')}</td>
                <td className="px-3 py-2 font-mono text-xs">{t.ip_allowlist.join(', ') || '—'}</td>
                <td className="px-3 py-2 text-text-secondary">{t.last_used_at ?? 'never'}</td>
              </tr>
            ))}
            {(data ?? []).length === 0 && (
              <tr><td colSpan={5} className="px-3 py-4 text-text-secondary">No tokens.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
