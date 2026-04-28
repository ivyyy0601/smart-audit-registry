import React, { useState } from 'react'
import { Routes, Route, NavLink } from 'react-router-dom'
import { ethers } from 'ethers'
import SubmitAudit from './pages/SubmitAudit'
import ViewAudit from './pages/ViewAudit'
import VerifyReport from './pages/VerifyReport'
import ReportView from './pages/ReportView'

const navStyle = ({ isActive }) => ({
  padding: '8px 16px',
  borderRadius: '6px',
  background: isActive ? '#1e40af' : 'transparent',
  color: isActive ? '#fff' : '#94a3b8',
  fontWeight: isActive ? 600 : 400,
})

const short = addr => addr ? `${addr.slice(0, 6)}...${addr.slice(-4)}` : ''

export default function App() {
  const [wallet, setWallet] = useState('')

  const connectWallet = async () => {
    if (!window.ethereum) return alert('Please install MetaMask')
    // Force MetaMask popup every time
    await window.ethereum.request({
      method: 'wallet_requestPermissions',
      params: [{ eth_accounts: {} }],
    })
    const provider = new ethers.BrowserProvider(window.ethereum)
    const accounts = await provider.send('eth_requestAccounts', [])
    setWallet(accounts[0])
  }

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
        <button onClick={connectWallet} style={{
          padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
          background: wallet ? '#166534' : '#1d4ed8', color: '#fff', fontWeight: 600,
        }}>
          {wallet ? short(wallet) : 'Connect Wallet'}
        </button>
      </nav>

      <main style={{ maxWidth: 800, margin: '48px auto', padding: '0 24px' }}>
        <Routes>
          <Route path="/"            element={<SubmitAudit wallet={wallet} />} />
          <Route path="/view"        element={<ViewAudit />} />
          <Route path="/verify"      element={<VerifyReport />} />
          <Route path="/report/:hash" element={<ReportView />} />
        </Routes>
      </main>
    </div>
  )
}
