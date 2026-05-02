import Modal from './Modal'

interface Props {
  title: string
  message: string
  confirmLabel?: string
  danger?: boolean
  onConfirm: () => void
  onClose: () => void
  busy?: boolean
  error?: string | null
}

export default function ConfirmModal({ title, message, confirmLabel = 'Confirm', danger = false, onConfirm, onClose, busy = false, error = null }: Props) {
  return (
    <Modal
      title={title}
      onClose={onClose}
      footer={
        <>
          <button onClick={onClose} disabled={busy} className="px-3 py-1.5 rounded bg-bg-tertiary hover:bg-bg-secondary text-sm">Cancel</button>
          <button
            onClick={onConfirm}
            disabled={busy}
            className={`px-3 py-1.5 rounded text-sm text-white ${danger ? 'bg-red-700 hover:bg-red-800' : 'bg-accent hover:bg-accent-hover'} disabled:opacity-50`}
          >
            {busy ? 'Working…' : confirmLabel}
          </button>
        </>
      }
    >
      <p className="text-sm">{message}</p>
      {error && <p className="text-red-400 text-sm mt-3">{error}</p>}
    </Modal>
  )
}
