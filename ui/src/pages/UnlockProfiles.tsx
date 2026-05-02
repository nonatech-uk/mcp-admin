import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

interface UnlockProfile {
  id: string
  name: string
  key_preview: string
  tools_glob: string[]
  created_at: string
  created_by: string
  revoked_at: string | null
}

export default function UnlockProfiles() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['unlock_profiles'],
    queryFn: () => api<UnlockProfile[]>('/unlock_profiles'),
  })

  if (isLoading) return <div className="text-text-secondary">Loading…</div>
  if (error) return <div className="text-red-500">{(error as Error).message}</div>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Unlock profiles</h1>
      <p className="text-text-secondary text-sm mb-4">
        Each profile carries a key + tool-scope intersection. Phase 2 wires the
        gateway to look these up; today only the legacy <code>default</code>
        profile is consumed.
      </p>
      <div className="overflow-x-auto rounded border border-border">
        <table className="w-full text-sm">
          <thead className="bg-bg-secondary text-text-secondary">
            <tr>
              <th className="text-left px-3 py-2">Name</th>
              <th className="text-left px-3 py-2">Preview</th>
              <th className="text-left px-3 py-2">Tools</th>
              <th className="text-left px-3 py-2">Created</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((p) => (
              <tr key={p.id} className="border-t border-border">
                <td className="px-3 py-2 font-medium">{p.name}</td>
                <td className="px-3 py-2 font-mono text-xs">{p.key_preview}…</td>
                <td className="px-3 py-2 font-mono text-xs">{p.tools_glob.join(', ')}</td>
                <td className="px-3 py-2 text-text-secondary">{p.created_at}</td>
              </tr>
            ))}
            {(data ?? []).length === 0 && (
              <tr><td colSpan={4} className="px-3 py-4 text-text-secondary">No unlock profiles.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
