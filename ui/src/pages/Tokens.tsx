import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, apiDelete, apiPatch, apiPost } from '../api/client'
import Modal from '../components/Modal'
import RevealModal from '../components/RevealModal'
import ConfirmModal from '../components/ConfirmModal'

interface Token {
  id: string
  name: string
  token_preview: string
  tools_glob: string[]
  ip_allowlist: string[]
  host_allowlist: string[]
  created_at: string
  created_by: string
  last_used_at: string | null
  revoked_at: string | null
}

interface TokenWithCleartext extends Token { token: string }

function fromLines(text: string): string[] {
  return text.split('\n').map((s) => s.trim()).filter((s) => s.length > 0)
}

export default function Tokens() {
  const qc = useQueryClient()
  const { data, isLoading, error } = useQuery({
    queryKey: ['tokens'],
    queryFn: () => api<Token[]>('/tokens'),
  })

  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<Token | null>(null)
  const [revoking, setRevoking] = useState<Token | null>(null)
  const [rotating, setRotating] = useState<Token | null>(null)
  const [reveal, setReveal] = useState<{ title: string; cleartext: string } | null>(null)

  const invalidate = () => qc.invalidateQueries({ queryKey: ['tokens'] })

  if (isLoading) return <div className="text-text-secondary">Loading…</div>
  if (error) return <div className="text-red-500">{(error as Error).message}</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Static tokens</h1>
        <button
          onClick={() => setCreating(true)}
          className="px-3 py-1.5 rounded bg-accent hover:bg-accent-hover text-white text-sm"
        >+ New token</button>
      </div>
      <p className="text-text-secondary text-sm mb-4">
        Bearer tokens for non-claude.ai callers (Claude Code CLI, scripts).
        Cleartext is shown only once at create / rotate time.
      </p>
      <div className="overflow-x-auto rounded border border-border">
        <table className="w-full text-sm">
          <thead className="bg-bg-secondary text-text-secondary">
            <tr>
              <th className="text-left px-3 py-2">Name</th>
              <th className="text-left px-3 py-2">Preview</th>
              <th className="text-left px-3 py-2">Tools</th>
              <th className="text-left px-3 py-2">IP allowlist</th>
              <th className="text-left px-3 py-2">Host allowlist</th>
              <th className="text-left px-3 py-2">Last used</th>
              <th className="text-right px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((t) => (
              <tr key={t.id} className="border-t border-border">
                <td className="px-3 py-2 font-medium">{t.name}</td>
                <td className="px-3 py-2 font-mono text-xs">{t.token_preview}…</td>
                <td className="px-3 py-2 font-mono text-xs">{t.tools_glob.join(', ')}</td>
                <td className="px-3 py-2 font-mono text-xs">{t.ip_allowlist.join(', ') || '—'}</td>
                <td className="px-3 py-2 font-mono text-xs">{t.host_allowlist.join(', ') || '—'}</td>
                <td className="px-3 py-2 text-text-secondary">{t.last_used_at ?? 'never'}</td>
                <td className="px-3 py-2 text-right whitespace-nowrap">
                  <button onClick={() => setEditing(t)} className="text-text-secondary hover:text-text-primary mr-3">Edit</button>
                  <button onClick={() => setRotating(t)} className="text-text-secondary hover:text-text-primary mr-3">Rotate</button>
                  <button onClick={() => setRevoking(t)} className="text-red-400 hover:text-red-300">Revoke</button>
                </td>
              </tr>
            ))}
            {(data ?? []).length === 0 && (
              <tr><td colSpan={7} className="px-3 py-4 text-text-secondary">No tokens. Create one above.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {creating && (
        <CreateModal
          onClose={() => setCreating(false)}
          onCreated={(t) => { setReveal({ title: `Bearer for ${t.name}`, cleartext: t.token }); invalidate() }}
        />
      )}
      {editing && (
        <EditModal token={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); invalidate() }} />
      )}
      {rotating && (
        <RotateConfirm
          token={rotating}
          onClose={() => setRotating(null)}
          onRotated={(t) => { setRotating(null); setReveal({ title: `New bearer for ${t.name}`, cleartext: t.token }); invalidate() }}
        />
      )}
      {revoking && (
        <RevokeConfirm token={revoking} onClose={() => setRevoking(null)} onRevoked={() => { setRevoking(null); invalidate() }} />
      )}
      {reveal && <RevealModal title={reveal.title} cleartext={reveal.cleartext} onClose={() => setReveal(null)} />}
    </div>
  )
}

function CreateModal({ onClose, onCreated }: { onClose: () => void; onCreated: (t: TokenWithCleartext) => void }) {
  const [name, setName] = useState('')
  const [tools, setTools] = useState('')
  const [ips, setIps] = useState('')
  const [hosts, setHosts] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const m = useMutation({
    mutationFn: () => apiPost<TokenWithCleartext>('/tokens', {
      name,
      tools_glob: fromLines(tools),
      ip_allowlist: fromLines(ips),
      host_allowlist: fromLines(hosts),
    }),
    onSuccess: (t) => { onCreated(t); onClose() },
    onError: (e: Error) => setErr(e.message),
  })
  return (
    <Modal
      title="New static token"
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose} className="px-3 py-1.5 rounded bg-bg-tertiary text-sm">Cancel</button>
          <button
            onClick={() => { setErr(null); m.mutate() }}
            disabled={m.isPending || !name}
            className="px-3 py-1.5 rounded bg-accent hover:bg-accent-hover text-white text-sm disabled:opacity-50"
          >{m.isPending ? 'Creating…' : 'Create'}</button>
        </>
      }
    >
      <Field label="Name" hint="Lowercase, no spaces (e.g. albury-app-server)">
        <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} autoFocus />
      </Field>
      <Field label="Tool patterns" hint="One glob per line (e.g. ha_albury_*). At least one.">
        <textarea value={tools} onChange={(e) => setTools(e.target.value)} rows={4} className={inputCls} />
      </Field>
      <Field label="IP allowlist (CIDRs)" hint="One per line. Empty = allow from any IP.">
        <textarea value={ips} onChange={(e) => setIps(e.target.value)} rows={3} className={inputCls} />
      </Field>
      <Field label="Host allowlist" hint="One hostname per line; '*' for any host. Empty = deny all hosts (host_tools_*, logs_*).">
        <textarea value={hosts} onChange={(e) => setHosts(e.target.value)} rows={3} className={inputCls} />
      </Field>
      {err && <p className="text-red-400 text-sm mt-2">{err}</p>}
    </Modal>
  )
}

function EditModal({ token, onClose, onSaved }: { token: Token; onClose: () => void; onSaved: () => void }) {
  const [tools, setTools] = useState(token.tools_glob.join('\n'))
  const [ips, setIps] = useState(token.ip_allowlist.join('\n'))
  const [hosts, setHosts] = useState(token.host_allowlist.join('\n'))
  const [err, setErr] = useState<string | null>(null)
  const m = useMutation({
    mutationFn: () => apiPatch<Token>(`/tokens/${token.id}`, {
      tools_glob: fromLines(tools),
      ip_allowlist: fromLines(ips),
      host_allowlist: fromLines(hosts),
    }),
    onSuccess: () => onSaved(),
    onError: (e: Error) => setErr(e.message),
  })
  return (
    <Modal
      title={`Edit ${token.name}`}
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose} className="px-3 py-1.5 rounded bg-bg-tertiary text-sm">Cancel</button>
          <button
            onClick={() => { setErr(null); m.mutate() }}
            disabled={m.isPending}
            className="px-3 py-1.5 rounded bg-accent hover:bg-accent-hover text-white text-sm disabled:opacity-50"
          >{m.isPending ? 'Saving…' : 'Save'}</button>
        </>
      }
    >
      <Field label="Tool patterns" hint="One glob per line.">
        <textarea value={tools} onChange={(e) => setTools(e.target.value)} rows={4} className={inputCls} />
      </Field>
      <Field label="IP allowlist (CIDRs)" hint="One per line.">
        <textarea value={ips} onChange={(e) => setIps(e.target.value)} rows={3} className={inputCls} />
      </Field>
      <Field label="Host allowlist" hint="One hostname per line; '*' for any host. Empty = deny.">
        <textarea value={hosts} onChange={(e) => setHosts(e.target.value)} rows={3} className={inputCls} />
      </Field>
      {err && <p className="text-red-400 text-sm mt-2">{err}</p>}
    </Modal>
  )
}

function RotateConfirm({ token, onClose, onRotated }: { token: Token; onClose: () => void; onRotated: (t: TokenWithCleartext) => void }) {
  const m = useMutation({
    mutationFn: () => apiPost<TokenWithCleartext>(`/tokens/${token.id}/rotate`),
    onSuccess: (t) => onRotated(t),
  })
  return (
    <ConfirmModal
      title={`Rotate ${token.name}`}
      message={`The current bearer will stop working immediately. The new value is shown once. Continue?`}
      confirmLabel="Rotate"
      busy={m.isPending}
      onConfirm={() => m.mutate()}
      onClose={onClose}
    />
  )
}

function RevokeConfirm({ token, onClose, onRevoked }: { token: Token; onClose: () => void; onRevoked: () => void }) {
  const m = useMutation({
    mutationFn: () => apiDelete<Token>(`/tokens/${token.id}`),
    onSuccess: () => onRevoked(),
  })
  return (
    <ConfirmModal
      title={`Revoke ${token.name}`}
      message="This bearer will stop working immediately and cannot be restored. Existing sessions using it will lose access on their next request. Continue?"
      confirmLabel="Revoke"
      danger
      busy={m.isPending}
      onConfirm={() => m.mutate()}
      onClose={onClose}
    />
  )
}

const inputCls = 'w-full px-2 py-1.5 rounded border border-border bg-bg-secondary text-sm font-mono'

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <label className="block text-sm font-medium mb-1">{label}</label>
      {hint && <p className="text-xs text-text-secondary mb-1">{hint}</p>}
      {children}
    </div>
  )
}
