import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

interface Entry {
  id: number
  actor_email: string
  action: string
  target_type: string
  target_name: string
  ts: string
}

export default function Audit() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['audit'],
    queryFn: () => api<Entry[]>('/audit?limit=200'),
  })

  if (isLoading) return <div className="text-text-secondary">Loading…</div>
  if (error) return <div className="text-red-500">{(error as Error).message}</div>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Audit log</h1>
      <p className="text-text-secondary text-sm mb-4">
        Every mutation produced by Phase 2 will land here.
      </p>
      <div className="overflow-x-auto rounded border border-border">
        <table className="w-full text-sm">
          <thead className="bg-bg-secondary text-text-secondary">
            <tr>
              <th className="text-left px-3 py-2">When</th>
              <th className="text-left px-3 py-2">Actor</th>
              <th className="text-left px-3 py-2">Action</th>
              <th className="text-left px-3 py-2">Target</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((e) => (
              <tr key={e.id} className="border-t border-border">
                <td className="px-3 py-2 text-text-secondary whitespace-nowrap">{e.ts}</td>
                <td className="px-3 py-2">{e.actor_email}</td>
                <td className="px-3 py-2 font-mono text-xs">{e.action}</td>
                <td className="px-3 py-2 font-mono text-xs">{e.target_type} / {e.target_name}</td>
              </tr>
            ))}
            {(data ?? []).length === 0 && (
              <tr><td colSpan={4} className="px-3 py-4 text-text-secondary">No entries yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
