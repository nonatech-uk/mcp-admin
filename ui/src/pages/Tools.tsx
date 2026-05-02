import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

interface Tool { name: string; description: string }
interface ToolsResp { tools: Tool[]; count: number }

export default function Tools() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['gateway_tools'],
    queryFn: () => api<ToolsResp>('/gateway/tools'),
  })
  const [filter, setFilter] = useState('')

  const grouped = useMemo(() => {
    const tools = (data?.tools ?? []).filter((t) =>
      !filter || t.name.toLowerCase().includes(filter.toLowerCase())
    )
    const m = new Map<string, Tool[]>()
    for (const t of tools) {
      // group by leading prefix up to first underscore
      const prefix = t.name.split('_')[0] || '_'
      const arr = m.get(prefix) ?? []
      arr.push(t)
      m.set(prefix, arr)
    }
    return [...m.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [data, filter])

  if (isLoading) return <div className="text-text-secondary">Loading…</div>
  if (error) return <div className="text-red-500">{(error as Error).message}</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Tools</h1>
        <span className="text-sm text-text-secondary">
          {data?.count ?? 0} total
          {filter && ` · showing ${grouped.reduce((n, [, ts]) => n + ts.length, 0)}`}
        </span>
      </div>
      <p className="text-text-secondary text-sm mb-4">
        Live list from mcp-gateway. Use these names when authoring
        <code className="font-mono px-1">tools_glob</code> patterns
        (e.g. <code className="font-mono px-1">ha_albury_*</code>).
      </p>
      <input
        type="text"
        placeholder="Filter tools…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="w-full mb-4 px-3 py-2 rounded border border-border bg-bg-secondary text-sm font-mono"
        autoFocus
      />
      <div className="space-y-4">
        {grouped.map(([prefix, tools]) => (
          <details key={prefix} open className="rounded border border-border bg-bg-secondary">
            <summary className="px-3 py-2 cursor-pointer flex items-center gap-2">
              <span className="font-mono font-semibold">{prefix}_*</span>
              <span className="text-xs text-text-secondary">{tools.length}</span>
            </summary>
            <table className="w-full text-sm">
              <tbody>
                {tools.map((t) => (
                  <tr key={t.name} className="border-t border-border">
                    <td className="px-3 py-2 font-mono text-xs whitespace-nowrap align-top w-1/3">{t.name}</td>
                    <td className="px-3 py-2 text-text-secondary">{t.description || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        ))}
        {grouped.length === 0 && <div className="text-text-secondary">No tools match.</div>}
      </div>
    </div>
  )
}
