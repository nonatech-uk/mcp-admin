import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, apiDelete, apiPatch, apiPost } from '../api/client'
import Modal from '../components/Modal'
import RevealModal from '../components/RevealModal'
import ConfirmModal from '../components/ConfirmModal'

interface Profile {
  id: string
  name: string
  key_preview: string
  tools_glob: string[]
  created_at: string
  created_by: string
  revoked_at: string | null
}
interface ProfileWithKey extends Profile { key: string }

const inputCls = 'w-full px-2 py-1.5 rounded border border-border bg-bg-secondary text-sm font-mono'
const fromLines = (s: string) => s.split('\n').map((x) => x.trim()).filter(Boolean)

export default function UnlockProfiles() {
  const qc = useQueryClient()
  const { data, isLoading, error } = useQuery({ queryKey: ['unlock_profiles'], queryFn: () => api<Profile[]>('/unlock_profiles') })
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<Profile | null>(null)
  const [rotating, setRotating] = useState<Profile | null>(null)
  const [revoking, setRevoking] = useState<Profile | null>(null)
  const [reveal, setReveal] = useState<{ title: string; cleartext: string } | null>(null)
  const invalidate = () => qc.invalidateQueries({ queryKey: ['unlock_profiles'] })

  if (isLoading) return <div className="text-text-secondary">Loading…</div>
  if (error) return <div className="text-red-500">{(error as Error).message}</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Unlock profiles</h1>
        <button onClick={() => setCreating(true)} className="px-3 py-1.5 rounded bg-accent hover:bg-accent-hover text-white text-sm">+ New profile</button>
      </div>
      <p className="text-text-secondary text-sm mb-4">
        Profile-based session unlock. Each profile carries a key + tool-scope
        intersection. The session sees the intersection of the matched policy's
        tools and the unlocked profile's tools — narrows only, never widens.
      </p>
      <div className="overflow-x-auto rounded border border-border">
        <table className="w-full text-sm">
          <thead className="bg-bg-secondary text-text-secondary">
            <tr>
              <th className="text-left px-3 py-2">Name</th>
              <th className="text-left px-3 py-2">Preview</th>
              <th className="text-left px-3 py-2">Tools</th>
              <th className="text-left px-3 py-2">Created</th>
              <th className="text-right px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((p) => (
              <tr key={p.id} className="border-t border-border">
                <td className="px-3 py-2 font-medium">{p.name}</td>
                <td className="px-3 py-2 font-mono text-xs">{p.key_preview}…</td>
                <td className="px-3 py-2 font-mono text-xs">{p.tools_glob.join(', ')}</td>
                <td className="px-3 py-2 text-text-secondary">{p.created_at}</td>
                <td className="px-3 py-2 text-right whitespace-nowrap">
                  <button onClick={() => setEditing(p)} className="text-text-secondary hover:text-text-primary mr-3">Edit</button>
                  <button onClick={() => setRotating(p)} className="text-text-secondary hover:text-text-primary mr-3">Rotate</button>
                  <button onClick={() => setRevoking(p)} className="text-red-400 hover:text-red-300">Revoke</button>
                </td>
              </tr>
            ))}
            {(data ?? []).length === 0 && (
              <tr><td colSpan={5} className="px-3 py-4 text-text-secondary">No profiles.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {creating && <CreateProfile onClose={() => setCreating(false)} onCreated={(p) => { setReveal({ title: `Key for ${p.name}`, cleartext: p.key }); invalidate() }} />}
      {editing && <EditProfile profile={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); invalidate() }} />}
      {rotating && (
        <ConfirmModal
          title={`Rotate ${rotating.name}`}
          message="The current key will stop working immediately. New value shown once. Continue?"
          confirmLabel="Rotate"
          onConfirm={async () => {
            const p = await apiPost<ProfileWithKey>(`/unlock_profiles/${rotating!.id}/rotate`)
            setRotating(null)
            setReveal({ title: `New key for ${p.name}`, cleartext: p.key })
            invalidate()
          }}
          onClose={() => setRotating(null)}
        />
      )}
      {revoking && <RevokeProfile profile={revoking} onClose={() => setRevoking(null)} onRevoked={() => { setRevoking(null); invalidate() }} />}
      {reveal && <RevealModal title={reveal.title} cleartext={reveal.cleartext} onClose={() => setReveal(null)} />}
    </div>
  )
}

function RevokeProfile({ profile, onClose, onRevoked }: { profile: Profile; onClose: () => void; onRevoked: () => void }) {
  const [err, setErr] = useState<string | null>(null)
  const m = useMutation({
    mutationFn: () => apiDelete<Profile>(`/unlock_profiles/${profile.id}`),
    onSuccess: () => onRevoked(),
    onError: (e: Error) => setErr(e.message),
  })
  return (
    <ConfirmModal
      title={`Revoke ${profile.name}`}
      message={
        profile.name === 'default'
          ? "Revoking 'default' will lock out any caller still using gateway_unlock(key=…) without a profile. Continue?"
          : "This profile and its key stop working immediately. Cannot be restored. Continue?"
      }
      confirmLabel="Revoke"
      danger
      busy={m.isPending}
      error={err}
      onConfirm={() => { setErr(null); m.mutate() }}
      onClose={onClose}
    />
  )
}

function CreateProfile({ onClose, onCreated }: { onClose: () => void; onCreated: (p: ProfileWithKey) => void }) {
  const [name, setName] = useState('')
  const [tools, setTools] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const m = useMutation({
    mutationFn: () => apiPost<ProfileWithKey>('/unlock_profiles', { name, tools_glob: fromLines(tools) }),
    onSuccess: (p) => { onCreated(p); onClose() },
    onError: (e: Error) => setErr(e.message),
  })
  return (
    <Modal
      title="New unlock profile"
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose} className="px-3 py-1.5 rounded bg-bg-tertiary text-sm">Cancel</button>
          <button onClick={() => { setErr(null); m.mutate() }} disabled={m.isPending || !name} className="px-3 py-1.5 rounded bg-accent hover:bg-accent-hover text-white text-sm disabled:opacity-50">{m.isPending ? 'Creating…' : 'Create'}</button>
        </>
      }
    >
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Name</label>
        <p className="text-xs text-text-secondary mb-1">Lowercase, no spaces (e.g. albury-only).</p>
        <input value={name} onChange={(e) => setName(e.target.value)} className={inputCls} autoFocus />
      </div>
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Tool patterns</label>
        <p className="text-xs text-text-secondary mb-1">One glob per line. The session sees the intersection of these and the matched policy's tools.</p>
        <textarea value={tools} onChange={(e) => setTools(e.target.value)} rows={4} className={inputCls} />
      </div>
      {err && <p className="text-red-400 text-sm mt-2">{err}</p>}
    </Modal>
  )
}

function EditProfile({ profile, onClose, onSaved }: { profile: Profile; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(profile.name)
  const [tools, setTools] = useState(profile.tools_glob.join('\n'))
  const [err, setErr] = useState<string | null>(null)
  const isDefault = profile.name === 'default'
  const m = useMutation({
    mutationFn: () => {
      const body: { name?: string; tools_glob: string[] } = { tools_glob: fromLines(tools) }
      if (!isDefault && name !== profile.name) body.name = name
      return apiPatch<Profile>(`/unlock_profiles/${profile.id}`, body)
    },
    onSuccess: () => onSaved(),
    onError: (e: Error) => setErr(e.message),
  })
  return (
    <Modal
      title={`Edit ${profile.name}`}
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose} className="px-3 py-1.5 rounded bg-bg-tertiary text-sm">Cancel</button>
          <button onClick={() => { setErr(null); m.mutate() }} disabled={m.isPending || (!isDefault && !name)} className="px-3 py-1.5 rounded bg-accent hover:bg-accent-hover text-white text-sm disabled:opacity-50">{m.isPending ? 'Saving…' : 'Save'}</button>
        </>
      }
    >
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Name</label>
        {isDefault && <p className="text-xs text-text-secondary mb-1">The 'default' profile cannot be renamed (legacy callers depend on it).</p>}
        <input value={name} onChange={(e) => setName(e.target.value)} disabled={isDefault} className={inputCls + (isDefault ? ' opacity-50 cursor-not-allowed' : '')} />
      </div>
      <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Tool patterns</label>
        <textarea value={tools} onChange={(e) => setTools(e.target.value)} rows={4} className={inputCls} />
      </div>
      {err && <p className="text-red-400 text-sm mt-2">{err}</p>}
    </Modal>
  )
}
