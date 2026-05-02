import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

interface Entry {
  id: number
  ts: string
  event: string
  actor_kind: string | null
  actor_name: string | null
  client_ip: string | null
  tool_name: string | null
  profile: string | null
  detail: unknown
}

const eventColor: Record<string, string> = {
  auth_success: 'text-green-400',
  auth_fail_token: 'text-red-400',
  auth_fail_ip: 'text-red-400',
  unlock_success: 'text-green-400',
  unlock_fail: 'text-red-400',
  tool_deny: 'text-red-400',
  tool_allow: 'text-text-secondary',
}

const EVENTS = ['', 'auth_success', 'auth_fail_token', 'auth_fail_ip', 'unlock_success', 'unlock_fail', 'tool_deny']

export default function AccessLog() {
  const [event, setEvent] = useState('')
  const [actor, setActor] = useState('')

  const qs = new URLSearchParams({ limit: '500' })
  if (event) qs.set('event', event)
  if (actor) qs.set('actor_name', actor)

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['access_log', event, actor],
    queryFn: () => api<Entry[]>(`/access_log?${qs.toString()}`),
  })

  if (isLoading) return <div className="text-text-secondary">Loading…</div>
  if (error) return <div className="text-red-500">{(error as Error).message}</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Access log</h1>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="px-3 py-1.5 rounded bg-bg-tertiary hover:bg-bg-secondary text-sm disabled:opacity-50"
        >{isFetching ? 'Loading…' : 'Refresh'}</button>
      </div>
      <p className="text-text-secondary text-sm mb-4">
        Per-request events from mcp-gateway: every authentication match, every
        unlock attempt, every blocked tool call. Newest first.
      </p>
      <div className="flex gap-3 mb-4">
        <div>
          <label className="block text-xs text-text-secondary mb-1">Event</label>
          <select value={event} onChange={(e) => setEvent(e.target.value)} className="px-2 py-1.5 rounded border border-border bg-bg-secondary text-sm font-mono">
            {EVENTS.map((e) => <option key={e} value={e}>{e || 'all'}</option>)}
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-xs text-text-secondary mb-1">Actor name</label>
          <input value={actor} onChange={(e) => setActor(e.target.value)} placeholder="claude-code-cli, stu-admin, …" className="w-full px-2 py-1.5 rounded border border-border bg-bg-secondary text-sm font-mono" />
        </div>
      </div>
      <div className="overflow-x-auto rounded border border-border">
        <table className="w-full text-sm">
          <thead className="bg-bg-secondary text-text-secondary">
            <tr>
              <th className="text-left px-3 py-2">When</th>
              <th className="text-left px-3 py-2">Event</th>
              <th className="text-left px-3 py-2">Actor</th>
              <th className="text-left px-3 py-2">IP</th>
              <th className="text-left px-3 py-2">Tool</th>
              <th className="text-left px-3 py-2">Profile</th>
              <th className="text-left px-3 py-2">Detail</th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((e) => (
              <tr key={e.id} className="border-t border-border align-top">
                <td className="px-3 py-2 text-text-secondary whitespace-nowrap">{e.ts.replace('T', ' ').slice(0, 19)}</td>
                <td className={`px-3 py-2 font-mono text-xs whitespace-nowrap ${eventColor[e.event] ?? ''}`}>{e.event}</td>
                <td className="px-3 py-2 font-mono text-xs">{e.actor_name || (e.actor_kind ? `(${e.actor_kind})` : '—')}</td>
                <td className="px-3 py-2 font-mono text-xs">{e.client_ip || '—'}</td>
                <td className="px-3 py-2 font-mono text-xs">{e.tool_name || '—'}</td>
                <td className="px-3 py-2 font-mono text-xs">{e.profile || '—'}</td>
                <td className="px-3 py-2 font-mono text-xs text-text-secondary break-all">{e.detail ? JSON.stringify(e.detail) : ''}</td>
              </tr>
            ))}
            {(data ?? []).length === 0 && (
              <tr><td colSpan={7} className="px-3 py-4 text-text-secondary">No entries match.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
