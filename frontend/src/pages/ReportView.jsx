import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api'

const SEV_COLOR = { HIGH: '#ef4444', MEDIUM: '#f97316', LOW: '#eab308' }
const SEV_BG    = { HIGH: '#450a0a', MEDIUM: '#431407', LOW: '#422006' }

function FindingCard({ f, index }) {
  const [open, setOpen] = useState(index === 0)
  const sev = f.severity || 'LOW'
  return (
    <div style={{ borderRadius: 8, overflow: 'hidden', marginBottom: 8,
      border: `1px solid ${SEV_COLOR[sev]}44` }}>
      <div onClick={() => setOpen(!open)} style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '12px 16px', cursor: 'pointer', background: SEV_BG[sev] + '88',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ color: SEV_COLOR[sev], fontWeight: 700, fontSize: 12,
            padding: '2px 8px', borderRadius: 4, background: SEV_COLOR[sev] + '22' }}>
            {sev}
          </span>
          <span style={{ fontWeight: 600, fontSize: 14 }}>{f.type || 'Unknown'}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, color: '#475569' }}>{f.function}</span>
          <span style={{ color: '#64748b' }}>{open ? '▲' : '▼'}</span>
        </div>
      </div>
      {open && (
        <div style={{ padding: '14px 16px', background: '#0f172a',
          borderTop: `1px solid ${SEV_COLOR[sev]}22` }}>
          <p style={{ fontSize: 13, color: '#cbd5e1', lineHeight: 1.7, marginBottom: 10 }}>
            {f.description}
          </p>
          <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#475569' }}>
            <span>📄 {f.contract}</span>
            <span>📍 Line {f.start_line}–{f.end_line}</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default function ReportView() {
  const { hash } = useParams()
  const navigate = useNavigate()
  const [report, setReport] = useState(null)
  const [error, setError]   = useState('')

  useEffect(() => {
    api.get(`/report/${encodeURIComponent(hash)}`)
      .then(r => setReport(r.data))
      .catch(err => setError(err.response?.data?.detail || 'Report not found'))
  }, [hash])

  const riskColor = s => s >= 70 ? '#ef4444' : s >= 40 ? '#f97316' : '#22c55e'
  const riskLabel = s => s >= 70 ? 'High Risk' : s >= 40 ? 'Medium Risk' : 'Low Risk'

  return (
    <div>
      <button onClick={() => navigate(-1)} style={{
        marginBottom: 20, padding: '6px 14px', borderRadius: 6, border: 'none',
        background: '#1e293b', color: '#94a3b8', cursor: 'pointer', fontSize: 13,
      }}>
        ← Back
      </button>

      <h1 style={{ marginBottom: 4 }}>Full Audit Report</h1>
      <p style={{ color: '#475569', fontSize: 12, marginBottom: 24, wordBreak: 'break-all' }}>
        IPFS:{' '}
        <a
          href={`https://lime-defensive-lynx-64.mypinata.cloud/ipfs/${hash}?pinataGatewayToken=jEc6RVLm6uMVD5p-3UALlnFQV5D2pZQDiH1LjKb5katYDOV2WrE5XV-bf0I4NBVQ`}
          target="_blank" rel="noreferrer"
          style={{ color: '#38bdf8' }}
        >
          {hash}
        </a>
      </p>

      {error && (
        <div style={{ padding: 20, background: '#1e293b', borderRadius: 12 }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>📦</div>
          <div style={{ fontWeight: 600, marginBottom: 8, color: '#e2e8f0' }}>
            Report Not in Local Cache
          </div>
          <div style={{ color: '#94a3b8', fontSize: 14, lineHeight: 1.7 }}>
            This report was created in a previous session and is stored on IPFS.<br />
            To view the full details, go back and re-submit the same contract — the new report will be immediately viewable.
          </div>
          <div style={{ marginTop: 12, padding: '8px 12px', background: '#0f172a',
            borderRadius: 8, fontSize: 12, color: '#475569', wordBreak: 'break-all' }}>
            IPFS CID: {hash}
          </div>
        </div>
      )}

      {!report && !error && (
        <div style={{ color: '#64748b' }}>Loading report…</div>
      )}

      {report && (() => {
        const score = report.risk_score
        const color = riskColor(score)
        const high   = (report.findings || []).filter(f => f.severity === 'HIGH').length
        const medium = (report.findings || []).filter(f => f.severity === 'MEDIUM').length
        const low    = (report.findings || []).filter(f => f.severity === 'LOW').length
        return (
          <div>
            {/* Header card */}
            <div style={{ background: '#1e293b', borderRadius: 16, padding: 28, marginBottom: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between',
                alignItems: 'flex-start', marginBottom: 20 }}>
                <div>
                  <h2 style={{ fontSize: 16, marginBottom: 4 }}>
                    {report.contract_identifier}
                  </h2>
                  <span style={{ fontSize: 12, color: '#475569' }}>
                    {report.functions_analyzed} functions analyzed
                  </span>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 48, fontWeight: 800, color, lineHeight: 1 }}>{score}</div>
                  <div style={{ fontSize: 12, color: '#64748b' }}>/ 100</div>
                  <div style={{ marginTop: 6, padding: '3px 12px', borderRadius: 20,
                    background: color + '22', color, fontSize: 12, fontWeight: 600,
                    display: 'inline-block' }}>
                    {riskLabel(score)}
                  </div>
                </div>
              </div>

              {/* Score bar */}
              <div style={{ height: 8, background: '#0f172a', borderRadius: 4, marginBottom: 20 }}>
                <div style={{ width: `${score}%`, height: '100%', background: color,
                  borderRadius: 4, transition: 'width .6s ease' }} />
              </div>

              {/* Summary */}
              <p style={{ color: '#94a3b8', lineHeight: 1.7, fontSize: 14,
                background: '#0f172a', padding: 14, borderRadius: 8 }}>
                {report.summary}
              </p>
            </div>

            {/* Stats */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
              gap: 10, marginBottom: 20 }}>
              {[
                { label: 'Total',  value: report.findings?.length ?? 0, color: '#38bdf8' },
                { label: 'High',   value: high,   color: '#ef4444' },
                { label: 'Medium', value: medium, color: '#f97316' },
                { label: 'Low',    value: low,    color: '#eab308' },
              ].map(s => (
                <div key={s.label} style={{ background: '#1e293b', borderRadius: 8,
                  padding: '16px 0', textAlign: 'center' }}>
                  <div style={{ fontSize: 28, fontWeight: 700, color: s.color }}>{s.value}</div>
                  <div style={{ fontSize: 12, color: '#475569', marginTop: 2 }}>{s.label}</div>
                </div>
              ))}
            </div>

            {/* Findings */}
            {report.findings && report.findings.length > 0 && (
              <div style={{ background: '#1e293b', borderRadius: 16, padding: 24 }}>
                <h3 style={{ marginBottom: 16, fontSize: 15 }}>
                  Vulnerabilities ({report.findings.length})
                </h3>
                {report.findings.map((f, i) => (
                  <FindingCard key={i} f={f} index={i} />
                ))}
              </div>
            )}
          </div>
        )
      })()}
    </div>
  )
}
