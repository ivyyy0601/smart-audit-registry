import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'

const riskColor = s => s >= 70 ? '#ef4444' : s >= 40 ? '#f97316' : '#22c55e'
const riskLabel = s => s >= 70 ? 'High Risk' : s >= 40 ? 'Medium Risk' : 'Low Risk'
const formatDate = ts => new Date(ts * 1000).toLocaleString()

function AuditCard({ record, isLatest, identifier }) {
  const [open, setOpen] = useState(isLatest)
  const navigate = useNavigate()
  const color = riskColor(record.risk_score)
  const isIPFS = record.report_hash && record.report_hash.startsWith('baf')

  return (
    <div style={{ borderRadius: 12, overflow: 'hidden', marginBottom: 12,
      border: `1px solid ${open ? color + '44' : '#1e293b'}`,
      background: '#1e293b' }}>

      {/* Card header — always visible */}
      <div onClick={() => setOpen(!open)} style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 18px', cursor: 'pointer',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {isLatest && (
            <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 20,
              background: '#1d4ed8', color: '#fff', fontWeight: 600 }}>LATEST</span>
          )}
          <span style={{ fontSize: 22, fontWeight: 800, color }}>
            {record.risk_score}
          </span>
          <span style={{ fontSize: 12, color: '#64748b' }}>/ 100</span>
          <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 4,
            background: color + '22', color, fontWeight: 600 }}>
            {riskLabel(record.risk_score)}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 12, color: '#64748b' }}>{formatDate(record.timestamp)}</span>
          <span style={{ color: '#64748b' }}>{open ? '▲' : '▼'}</span>
        </div>
      </div>

      {/* Expanded details */}
      {open && (
        <div style={{ padding: '0 18px 18px', borderTop: '1px solid #0f172a' }}>

          {/* Summary */}
          <p style={{ color: '#94a3b8', lineHeight: 1.7, margin: '14px 0',
            background: '#0f172a', padding: 12, borderRadius: 8, fontSize: 13 }}>
            {record.summary}
          </p>

          {/* Details grid */}
          <div style={{ display: 'grid', gap: 8 }}>
            <Row label="Submitter" value={
              <a href={`https://sepolia.etherscan.io/address/${record.submitter}`}
                target="_blank" rel="noreferrer" style={{ color: '#38bdf8' }}>
                {record.submitter}
              </a>
            } />
            <Row label="IPFS Report" value={
              <span style={{ wordBreak: 'break-all', color: '#94a3b8' }}>
                {record.report_hash}
                <span style={{ display: 'inline-flex', gap: 6, marginLeft: 8 }}>
                  {isIPFS && (
                    <button
                      onClick={() => navigate(`/report/${record.report_hash}`)}
                      style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4,
                        border: 'none', background: '#0c4a6e', color: '#38bdf8', cursor: 'pointer' }}>
                      View →
                    </button>
                  )}
                  <button onClick={() => navigator.clipboard.writeText(record.report_hash)}
                    style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4,
                      border: 'none', background: '#1e293b', color: '#94a3b8', cursor: 'pointer' }}>
                    Copy
                  </button>
                </span>
              </span>
            } />
            <Row label="Timestamp" value={formatDate(record.timestamp)} />
          </div>

          <button
            onClick={() => navigate(`/verify?id=${encodeURIComponent(identifier)}&hash=${encodeURIComponent(record.report_hash)}`)}
            style={{ marginTop: 14, padding: '8px 16px', borderRadius: 6, border: 'none',
              background: '#1d4ed8', color: '#fff', cursor: 'pointer', fontSize: 13 }}>
            Verify This Report →
          </button>
        </div>
      )}
    </div>
  )
}

export default function ViewAudit() {
  const [identifier, setIdentifier] = useState('')
  const [data, setData]             = useState(null)
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState('')

  const handleQuery = async (e) => {
    e.preventDefault()
    setError('')
    setData(null)
    setLoading(true)
    try {
      const res = await api.get(`/audit/${encodeURIComponent(identifier)}`)
      setData(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'No record found')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>View Audit Record</h1>
      <p style={{ color: '#64748b', marginBottom: 24 }}>
        Query all on-chain audit history by contract address or filename.
      </p>

      <form onSubmit={handleQuery} style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        <input
          type="text" value={identifier} onChange={e => setIdentifier(e.target.value)}
          placeholder="VulnerableToken.sol or 0x..." required
          style={{ flex: 1, padding: '10px 14px', borderRadius: 8,
            border: '1px solid #334155', background: '#1e293b', color: '#e2e8f0', fontSize: 14 }}
        />
        <button type="submit" disabled={loading} style={{
          padding: '10px 24px', borderRadius: 8, border: 'none',
          background: '#1d4ed8', color: '#fff', fontWeight: 600, cursor: 'pointer',
        }}>
          {loading ? '...' : 'Query'}
        </button>
      </form>

      {error && (
        <div style={{ padding: 14, background: '#450a0a', borderRadius: 8, color: '#fca5a5' }}>
          {error}
        </div>
      )}

      {data && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between',
            alignItems: 'center', marginBottom: 16 }}>
            <h2 style={{ fontSize: 16 }}>
              {data.contract_identifier}
            </h2>
            <span style={{ fontSize: 13, color: '#64748b' }}>
              {data.total} audit{data.total > 1 ? 's' : ''} found
            </span>
          </div>

          {/* Show records newest first */}
          {[...data.records].reverse().map((r, i) => (
            <AuditCard key={r.index} record={r} isLatest={i === 0} identifier={identifier} />
          ))}
        </div>
      )}
    </div>
  )
}

function Row({ label, value }) {
  return (
    <div style={{ display: 'flex', gap: 12, padding: '8px 0',
      borderBottom: '1px solid #0f172a' }}>
      <span style={{ color: '#475569', minWidth: 100, fontSize: 12, flexShrink: 0 }}>{label}</span>
      <span style={{ color: '#e2e8f0', fontSize: 12 }}>{value}</span>
    </div>
  )
}
