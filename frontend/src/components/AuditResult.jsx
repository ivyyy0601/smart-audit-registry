import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const SEVERITY_COLOR = { HIGH: '#ef4444', MEDIUM: '#f97316', LOW: '#eab308' }
const SEVERITY_BG    = { HIGH: '#450a0a', MEDIUM: '#431407', LOW: '#422006' }

function ScoreGauge({ score }) {
  const color = score >= 70 ? '#ef4444' : score >= 40 ? '#f97316' : '#22c55e'
  const label = score >= 70 ? 'High Risk' : score >= 40 ? 'Medium Risk' : 'Low Risk'
  return (
    <div style={{ textAlign: 'center', padding: '24px 0' }}>
      <div style={{ fontSize: 56, fontWeight: 800, color, lineHeight: 1 }}>{score}</div>
      <div style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>/ 100 Risk Score</div>
      <div style={{ display: 'inline-block', marginTop: 8, padding: '3px 12px',
        borderRadius: 20, background: color + '22', color, fontSize: 12, fontWeight: 600 }}>
        {label}
      </div>
      <div style={{ marginTop: 16, height: 8, background: '#1e293b', borderRadius: 4 }}>
        <div style={{ width: `${score}%`, height: '100%', background: color,
          borderRadius: 4, transition: 'width .6s ease' }} />
      </div>
    </div>
  )
}

function FindingCard({ f, index }) {
  const [open, setOpen] = useState(false)
  const sev = f.severity || 'LOW'
  return (
    <div style={{ borderRadius: 8, overflow: 'hidden', marginBottom: 8,
      border: `1px solid ${SEVERITY_COLOR[sev]}44` }}>
      <div onClick={() => setOpen(!open)} style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '12px 16px', cursor: 'pointer', background: SEVERITY_BG[sev] + '88',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ color: SEVERITY_COLOR[sev], fontWeight: 700, fontSize: 12,
            padding: '2px 8px', borderRadius: 4, background: SEVERITY_COLOR[sev] + '22' }}>
            {sev}
          </span>
          <span style={{ fontWeight: 600 }}>{f.type || 'Unknown'}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, color: '#475569' }}>{f.function}</span>
          <span style={{ color: '#64748b' }}>{open ? '▲' : '▼'}</span>
        </div>
      </div>
      {open && (
        <div style={{ padding: '14px 16px', background: '#0f172a', borderTop: `1px solid ${SEVERITY_COLOR[sev]}22` }}>
          <p style={{ fontSize: 13, color: '#cbd5e1', lineHeight: 1.7, marginBottom: 10 }}>
            {f.description}
          </p>
          <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#475569' }}>
            <span>📄 {f.contract}</span>
            <span>📍 Line {f.start_line} – {f.end_line}</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default function AuditResult({ data }) {
  if (!data) return null
  const navigate = useNavigate()
  const { risk_score, summary, report_hash, tx_hash, findings_count, findings, is_proxy } = data
  const high   = (findings || []).filter(f => f.severity === 'HIGH').length
  const medium = (findings || []).filter(f => f.severity === 'MEDIUM').length
  const low    = (findings || []).filter(f => f.severity === 'LOW').length
  const canViewReport = report_hash && report_hash.startsWith('baf')

  return (
    <div style={{ background: '#1e293b', borderRadius: 16, padding: 28, marginTop: 24 }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <h2 style={{ fontSize: 18 }}>Audit Complete</h2>
        <span style={{ fontSize: 12, color: '#22c55e', background: '#052e16',
          padding: '3px 10px', borderRadius: 20 }}>✅ On-chain</span>
      </div>

      {/* Score */}
      <ScoreGauge score={risk_score} />

      {/* Summary */}
      <p style={{ color: '#94a3b8', lineHeight: 1.7, marginBottom: 20,
        background: '#0f172a', padding: 14, borderRadius: 8, fontSize: 14 }}>
        {summary}
      </p>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 20 }}>
        <StatBox label="Total"   value={findings_count} color="#38bdf8" />
        <StatBox label="High"    value={high}   color="#ef4444" />
        <StatBox label="Medium"  value={medium} color="#f97316" />
        <StatBox label="Low"     value={low}    color="#eab308" />
      </div>

      {/* IPFS & Tx links */}
      <div style={{ display: 'grid', gap: 8, marginBottom: 20 }}>
        <LinkRow icon="📦" label="IPFS Report" value={report_hash}
          href={canViewReport ? `/report/${report_hash}` : null}
          hint="View Report"
          onNavigate={canViewReport ? () => navigate(`/report/${report_hash}`) : null}
          onCopy={() => { navigator.clipboard.writeText(report_hash) }} />
        {tx_hash && (
          <LinkRow icon="⛓️" label="Transaction" value={tx_hash}
            href={`https://sepolia.etherscan.io/tx/${tx_hash}`}
            hint="View on Etherscan" />
        )}
      </div>

      {/* Findings */}
      {findings && findings.length > 0 && (
        <div>
          <h3 style={{ marginBottom: 12, fontSize: 15 }}>
            Vulnerabilities Found ({findings.length})
          </h3>
          {findings.map((f, i) => <FindingCard key={i} f={f} index={i} />)}
        </div>
      )}
    </div>
  )
}

function StatBox({ label, value, color }) {
  return (
    <div style={{ background: '#0f172a', borderRadius: 8, padding: '12px 0', textAlign: 'center' }}>
      <div style={{ fontSize: 24, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 11, color: '#475569', marginTop: 2 }}>{label}</div>
    </div>
  )
}

function LinkRow({ icon, label, value, href, hint, onCopy, onNavigate }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = () => {
    if (onCopy) {
      onCopy()
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }
  return (
    <div style={{ background: '#0f172a', borderRadius: 8, padding: '10px 14px',
      display: 'flex', alignItems: 'center', gap: 10 }}>
      <span>{icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 11, color: '#475569', marginBottom: 2 }}>{label}</div>
        <div style={{ fontSize: 12, color: '#94a3b8', wordBreak: 'break-all' }}>
          {value}
        </div>
      </div>
      {href && onNavigate && (
        <button onClick={onNavigate}
          style={{ fontSize: 12, color: '#38bdf8', whiteSpace: 'nowrap',
            padding: '4px 10px', borderRadius: 6, background: '#0c4a6e',
            border: 'none', cursor: 'pointer' }}>
          {hint} →
        </button>
      )}
      {href && !onNavigate && (
        <a href={href} target="_blank" rel="noreferrer"
          style={{ fontSize: 12, color: '#38bdf8', whiteSpace: 'nowrap',
            padding: '4px 10px', borderRadius: 6, background: '#0c4a6e',
            textDecoration: 'none' }}>
          {hint} →
        </a>
      )}
      {onCopy && (
        <button onClick={handleCopy}
          style={{ fontSize: 12, color: copied ? '#22c55e' : '#38bdf8',
            whiteSpace: 'nowrap', padding: '4px 10px', borderRadius: 6,
            background: '#0c4a6e', border: 'none', cursor: 'pointer' }}>
          {copied ? '✅ Copied' : '📋 Copy'}
        </button>
      )}
    </div>
  )
}
