import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../api'

export default function VerifyReport() {
  const [searchParams] = useSearchParams()
  const [identifier, setIdentifier] = useState(searchParams.get('id') || '')
  const [reportHash, setReportHash] = useState(searchParams.get('hash') || '')

  useEffect(() => {
    if (searchParams.get('id') && searchParams.get('hash')) {
      document.querySelector('form')?.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    }
  }, [])
  const [result, setResult]         = useState(null)
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState('')

  const handleVerify = async (e) => {
    e.preventDefault()
    setError('')
    setResult(null)
    setLoading(true)
    try {
      const res = await api.get('/verify', {
        params: { contract_identifier: identifier, report_hash: reportHash }
      })
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>Verify Report</h1>
      <p style={{ color: '#64748b', marginBottom: 24 }}>
        Check whether an IPFS report hash matches the on-chain record — proving it has not been tampered with.
      </p>

      <form onSubmit={handleVerify}>
        <div style={{ marginBottom: 14 }}>
          <label style={{ display: 'block', marginBottom: 6, color: '#94a3b8' }}>Contract Identifier</label>
          <input
            type="text" value={identifier} onChange={e => setIdentifier(e.target.value)}
            placeholder="0x... or MyToken.sol" required style={inputStyle}
          />
        </div>
        <div style={{ marginBottom: 20 }}>
          <label style={{ display: 'block', marginBottom: 6, color: '#94a3b8' }}>IPFS Report Hash (CID)</label>
          <input
            type="text" value={reportHash} onChange={e => setReportHash(e.target.value)}
            placeholder="QmXxx..." required style={inputStyle}
          />
        </div>

        <button type="submit" disabled={loading} style={{
          width: '100%', padding: '12px', borderRadius: 8, border: 'none',
          background: loading ? '#334155' : '#1d4ed8', color: '#fff',
          fontWeight: 600, fontSize: 16, cursor: loading ? 'not-allowed' : 'pointer',
        }}>
          {loading ? 'Verifying…' : 'Verify'}
        </button>
      </form>

      {error && (
        <div style={{ marginTop: 16, padding: 14, background: '#450a0a', borderRadius: 8, color: '#fca5a5' }}>
          {error}
        </div>
      )}

      {result && (
        <div style={{
          marginTop: 24, padding: 24, borderRadius: 12, textAlign: 'center',
          background: result.matched ? '#052e16' : '#450a0a',
          border: `2px solid ${result.matched ? '#16a34a' : '#ef4444'}`,
        }}>
          <div style={{ fontSize: 48, marginBottom: 8 }}>
            {result.matched ? '✅' : '❌'}
          </div>
          <h2 style={{ color: result.matched ? '#22c55e' : '#ef4444', marginBottom: 8 }}>
            {result.matched ? 'Report Verified' : 'Verification Failed'}
          </h2>
          <p style={{ color: '#94a3b8' }}>
            {result.matched
              ? `This report hash matches on-chain record #${result.index}. The report has not been tampered with.`
              : 'This report hash does not match any on-chain record. The report may have been modified.'}
          </p>
        </div>
      )}
    </div>
  )
}

const inputStyle = {
  width: '100%', padding: '10px 14px', borderRadius: 8,
  border: '1px solid #334155', background: '#1e293b',
  color: '#e2e8f0', fontSize: 14,
}
