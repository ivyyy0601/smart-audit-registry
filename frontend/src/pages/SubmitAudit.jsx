import React, { useState } from 'react'
import api from '../api'
import AuditResult from '../components/AuditResult'

export default function SubmitAudit() {
  const [mode, setMode]       = useState('address')
  const [address, setAddress] = useState('')
  const [file, setFile]       = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult]   = useState(null)
  const [error, setError]     = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setResult(null)
    setLoading(true)
    try {
      let res
      if (mode === 'address') {
        res = await api.post('/audit/address', { contract_address: address })
      } else {
        const form = new FormData()
        form.append('file', file)
        res = await api.post('/audit/upload', form)
      }
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>Submit Audit</h1>
      <p style={{ color: '#64748b', marginBottom: 24 }}>
        Analyze a smart contract and store the result on-chain.
      </p>

      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        {['address', 'upload'].map(m => (
          <button key={m} onClick={() => setMode(m)} style={{
            padding: '6px 16px', borderRadius: 6, border: 'none', cursor: 'pointer',
            background: mode === m ? '#1d4ed8' : '#1e293b', color: '#fff',
          }}>
            {m === 'address' ? 'Contract Address' : 'Upload .sol File'}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit}>
        {mode === 'address' ? (
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 6, color: '#94a3b8' }}>
              Contract Address (must be verified on Etherscan)
            </label>
            <input
              type="text" value={address} onChange={e => setAddress(e.target.value)}
              placeholder="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
              required style={inputStyle}
            />
          </div>
        ) : (
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 6, color: '#94a3b8' }}>
              Upload .sol File
            </label>
            <input
              type="file" accept=".sol" onChange={e => setFile(e.target.files[0])}
              required style={{ ...inputStyle, padding: '10px' }}
            />
          </div>
        )}

        <button type="submit" disabled={loading} style={{
          width: '100%', padding: '12px', borderRadius: 8, border: 'none',
          background: loading ? '#334155' : '#1d4ed8', color: '#fff',
          fontWeight: 600, fontSize: 16, cursor: loading ? 'not-allowed' : 'pointer',
        }}>
          {loading ? 'Analyzing… (this may take 1–2 minutes)' : 'Run Audit'}
        </button>
      </form>

      {error && (
        <div style={{ marginTop: 16, padding: 14, background: '#450a0a', borderRadius: 8, color: '#fca5a5' }}>
          {error}
        </div>
      )}

      <AuditResult data={result} />
    </div>
  )
}

const inputStyle = {
  width: '100%', padding: '10px 14px', borderRadius: 8,
  border: '1px solid #334155', background: '#1e293b',
  color: '#e2e8f0', fontSize: 14,
}
