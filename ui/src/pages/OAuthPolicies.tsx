import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, apiDelete, apiPatch, apiPost } from '../api/client'
import Modal from '../components/Modal'
import ConfirmModal from '../components/ConfirmModal'

interface Policy {
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

const inputCls = 'w-full px-2 py-1.5 rounded border border-border bg-bg-secondary text-sm font-mono'
const fromLines = (s: string) => s.split('\n').map((x) => x.trim()).filter(Boolean)

export default function OAuthPolicies() {
  const qc = useQueryClient()
  const { data, isLoading, error } = useQuery({ queryKey: ['oauth_policies'], queryFn: () => api<Policy[]>('/oauth_policies') })
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<Policy | null>(null)
  const [revoking, setRevoking] = useState<Policy | null>(null)
  const invalidate = () => qc.invalidateQueries({ queryKey: ['oauth_policies'] })

  if (isLoading) return <div className="text-text-secondary">Loading…</div>
  if (error) return <div className="text-red-500">{(error as Error).message}</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">OAuth policies</h1>
        <button onClick={() => setCreating(true)} className="px-3 py-1.5 rounded bg-accent hover:bg-accent-hover text-white text-sm">+ New policy</button>
      </div>
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
              <div className="ml-auto whitespace-nowrap">
                <button onClick={() => setEditing(p)} className="text-text-secondary hover:text-text-primary text-sm mr-3">Edit</button>
                <button onClick={() => setRevoking(p)} className="text-red-400 hover:text-red-300 text-sm">Revoke</button>
              </div>
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

      {creating && <CreateOrEdit onClose={() => setCreating(false)} onSaved={() => { setCreating(false); invalidate() }} />}
      {editing && <CreateOrEdit policy={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); invalidate() }} />}
      {revoking && (
        <ConfirmModal
          title={`Revoke ${revoking.name}`}
          message="The matched user(s) will lose access immediately on their next request. Continue?"
          confirmLabel="Revoke"
          danger
          onConfirm={async () => { await apiDelete(`/oauth_policies/${revoking!.id}`); setRevoking(null); invalidate() }}
          onClose={() => setRevoking(null)}
        />
      )}
    </div>
  )
}

function CreateOrEdit({ policy, onClose, onSaved }: { policy?: Policy; onClose: () => void; onSaved: () => void }) {
  const isEdit = !!policy
  const [name, setName] = useState(policy?.name ?? '')
  const [subs, setSubs] = useState((policy?.oauth_sub ?? []).join('\n'))
  const [emails, setEmails] = useState((policy?.oauth_email ?? []).join('\n'))
  const [usernames, setUsernames] = useState((policy?.oauth_username ?? []).join('\n'))
  const [tools, setTools] = useState((policy?.tools_glob ?? []).join('\n'))
  const [ips, setIps] = useState((policy?.ip_allowlist ?? []).join('\n'))
  const [err, setErr] = useState<string | null>(null)

  const body = () => ({
    ...(isEdit ? {} : { name }),
    oauth_sub: fromLines(subs),
    oauth_email: fromLines(emails),
    oauth_username: fromLines(usernames),
    tools_glob: fromLines(tools),
    ip_allowlist: fromLines(ips),
  })

  const m = useMutation({
    mutationFn: () => isEdit
      ? apiPatch<Policy>(`/oauth_policies/${policy!.id}`, body())
      : apiPost<Policy>('/oauth_policies', body()),
    onSuccess: () => onSaved(),
    onError: (e: Error) => setErr(e.message),
  })

  return (
    <Modal
      title={isEdit ? `Edit ${policy!.name}` : 'New OAuth policy'}
      wide
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose} className="px-3 py-1.5 rounded bg-bg-tertiary text-sm">Cancel</button>
          <button onClick={() => { setErr(null); m.mutate() }} disabled={m.isPending || (!isEdit && !name)} className="px-3 py-1.5 rounded bg-accent hover:bg-accent-hover text-white text-sm disabled:opacity-50">{m.isPending ? 'Saving…' : isEdit ? 'Save' : 'Create'}</button>
        </>
      }
    >
      {!isEdit && (
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">Name</label>
          <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} autoFocus />
        </div>
      )}
      <p className="text-xs text-text-secondary mb-3">
        At least one of sub / email / username must be provided (any value matches).
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
        <ArrayField label="oauth_sub" hint="UUIDs from Keycloak" value={subs} onChange={setSubs} />
        <ArrayField label="oauth_email" hint="" value={emails} onChange={setEmails} />
        <ArrayField label="oauth_username" hint="preferred_username claim" value={usernames} onChange={setUsernames} />
      </div>
      <ArrayField label="Tool patterns (required)" hint="One glob per line" value={tools} onChange={setTools} rows={4} />
      <ArrayField label="IP allowlist (CIDRs)" hint="One per line. Empty = allow any." value={ips} onChange={setIps} />
      {err && <p className="text-red-400 text-sm mt-2">{err}</p>}
    </Modal>
  )
}

function ArrayField({ label, hint, value, onChange, rows = 3 }: { label: string; hint?: string; value: string; onChange: (s: string) => void; rows?: number }) {
  return (
    <div className="mb-2">
      <label className="block text-sm font-medium mb-1">{label}</label>
      {hint && <p className="text-xs text-text-secondary mb-1">{hint}</p>}
      <textarea value={value} onChange={(e) => onChange(e.target.value)} rows={rows} className={inputCls} />
    </div>
  )
}
