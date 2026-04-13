import React from 'react'
import { Routes, Route, NavLink } from 'react-router-dom'
import SubmitAudit from './pages/SubmitAudit'
import ViewAudit from './pages/ViewAudit'
import VerifyReport from './pages/VerifyReport'
import ReportView from './pages/ReportView'
import WalletConnect from './components/WalletConnect'

const navStyle = ({ isActive }) => ({
  padding: '8px 16px',
  borderRadius: '6px',
  background: isActive ? '#1e40af' : 'transparent',
  color: isActive ? '#fff' : '#94a3b8',
  fontWeight: isActive ? 600 : 400,
})

export default function App() {
  return (
    <div style={{ minHeight: '100vh' }}>
      <nav style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '16px 32px', borderBottom: '1px solid #1e293b', background: '#0f172a',
      }}>
        <span style={{ fontSize: 20, fontWeight: 700, color: '#38bdf8' }}>
          Smart Audit Registry
        </span>
        <div style={{ display: 'flex', gap: 8 }}>
          <NavLink to="/"       style={navStyle}>Submit Audit</NavLink>
          <NavLink to="/view"   style={navStyle}>View Record</NavLink>
          <NavLink to="/verify" style={navStyle}>Verify Report</NavLink>
        </div>
        <WalletConnect />
      </nav>

      <main style={{ maxWidth: 800, margin: '48px auto', padding: '0 24px' }}>
        <Routes>
          <Route path="/"            element={<SubmitAudit />} />
          <Route path="/view"        element={<ViewAudit />} />
          <Route path="/verify"      element={<VerifyReport />} />
          <Route path="/report/:hash" element={<ReportView />} />
        </Routes>
      </main>
    </div>
  )
}
