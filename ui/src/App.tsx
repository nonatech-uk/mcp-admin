import { BrowserRouter, NavLink, Routes, Route, Navigate } from 'react-router-dom'
import { Shell } from '@mees/shared-ui'
import Tokens from './pages/Tokens'
import OAuthPolicies from './pages/OAuthPolicies'
import UnlockProfiles from './pages/UnlockProfiles'
import Audit from './pages/Audit'
import Tools from './pages/Tools'
import AccessLog from './pages/AccessLog'

interface SidebarProps { className?: string; onNavigate?: () => void }

function Sidebar({ className = '', onNavigate }: SidebarProps) {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `block px-4 py-2 rounded text-sm ${
      isActive
        ? 'bg-bg-tertiary text-text-primary font-semibold'
        : 'text-text-secondary hover:text-text-primary hover:bg-bg-tertiary'
    }`
  return (
    <aside className={`w-56 flex-shrink-0 bg-bg-secondary border-r border-border flex flex-col ${className}`}>
      <div className="px-4 py-4 border-b border-border">
        <span className="text-lg font-bold text-accent">MCP Admin</span>
      </div>
      <nav className="flex-1 px-2 py-2 space-y-1">
        <NavLink to="/tokens" onClick={onNavigate} className={linkClass}>Static tokens</NavLink>
        <NavLink to="/oauth" onClick={onNavigate} className={linkClass}>OAuth policies</NavLink>
        <NavLink to="/unlock" onClick={onNavigate} className={linkClass}>Unlock profiles</NavLink>
        <NavLink to="/tools" onClick={onNavigate} className={linkClass}>Tools</NavLink>
        <NavLink to="/access" onClick={onNavigate} className={linkClass}>Access log</NavLink>
        <NavLink to="/audit" onClick={onNavigate} className={linkClass}>Audit log</NavLink>
      </nav>
      <div className="px-4 py-3 border-t border-border text-xs text-text-secondary">
        <a href="/auth/logout" className="hover:text-text-primary">Sign out</a>
      </div>
    </aside>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell appName="MCP Admin" sidebar={Sidebar}>
        <Routes>
          <Route path="/" element={<Navigate to="/tokens" replace />} />
          <Route path="/tokens" element={<Tokens />} />
          <Route path="/oauth" element={<OAuthPolicies />} />
          <Route path="/unlock" element={<UnlockProfiles />} />
          <Route path="/tools" element={<Tools />} />
          <Route path="/access" element={<AccessLog />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="*" element={<div className="text-text-secondary">Not found</div>} />
        </Routes>
      </Shell>
    </BrowserRouter>
  )
}
