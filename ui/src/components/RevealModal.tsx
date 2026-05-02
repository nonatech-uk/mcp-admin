import { useState } from 'react'
import Modal from './Modal'

interface Props {
  title: string
  cleartext: string
  warning?: string | null
  onClose: () => void
}

export default function RevealModal({ title, cleartext, warning, onClose }: Props) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(cleartext)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <Modal
      title={title}
      onClose={onClose}
      footer={<button onClick={onClose} className="px-3 py-1.5 rounded bg-bg-tertiary hover:bg-bg-secondary text-sm">Done</button>}
    >
      <p className="text-sm text-text-secondary mb-3">
        Copy this value now — it can never be retrieved again. Storing it elsewhere
        is your responsibility.
      </p>
      <div className="font-mono text-sm p-3 rounded bg-bg-secondary border border-border break-all">
        {cleartext}
      </div>
      <button
        onClick={copy}
        className="mt-3 px-3 py-1.5 rounded bg-accent hover:bg-accent-hover text-white text-sm"
      >
        {copied ? 'Copied' : 'Copy to clipboard'}
      </button>
      {warning && (
        <div className="mt-4 p-3 rounded bg-yellow-900/30 border border-yellow-700/40 text-sm text-yellow-200">
          ⚠ {warning}
        </div>
      )}
    </Modal>
  )
}
