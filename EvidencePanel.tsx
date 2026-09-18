import type { Risk } from '../api';

interface Props {
  risk: Risk | null;
  onClose: () => void;
  onViewDetail: (id: string) => void;
}

export default function EvidencePanel({ risk, onClose, onViewDetail }: Props) {
  if (!risk) return <div className="evidence-panel" />;

  return (
    <div className={`evidence-panel ${risk ? 'open' : ''}`}>
      <div className="evidence-panel-header">
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Evidence Trail</h3>
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <span className={`priority-badge ${risk.priority_band.toLowerCase()}`}>
              {risk.priority_band}
            </span>
            <span className={`risk-type-badge ${risk.risk_type}`}>
              {risk.risk_type.replace('_', ' ')}
            </span>
          </div>
        </div>
        <button className="evidence-panel-close" onClick={onClose}>✕</button>
      </div>

      {/* Risk Summary */}
      <div className="evidence-section">
        <div className="evidence-section-title">Risk Assessment</div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.6 }}>
          {risk.explanation}
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-md)', marginTop: 'var(--space-md)' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              {risk.severity_score.toFixed(1)}
            </div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Score</div>
          </div>
          {risk.financial_exposure != null && (
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                ${risk.financial_exposure.toLocaleString()}
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
                Exposure <span className={`source-badge ${risk.financial_source}`}>{risk.financial_source}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Evidence Trail */}
      {risk.evidence_trail && risk.evidence_trail.length > 0 && (
        <div className="evidence-section">
          <div className="evidence-section-title">Source Clauses</div>
          {risk.evidence_trail.map((ev, i) => (
            <div key={i}>
              <div className={`evidence-quote ${ev.label.toLowerCase().includes('contract') ? 'contract' : 'policy'}`}>
                <strong style={{ fontSize: '0.75rem' }}>{ev.label}</strong>
                <div style={{ marginTop: 6 }}>{ev.text}</div>
                <div className="evidence-citation">
                  {ev.page && `📄 Page ${ev.page}`} {ev.clause_id && `· ${ev.clause_id}`}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* LLM Reasoning */}
      {risk.llm_reasoning && (
        <div className="evidence-section">
          <div className="evidence-section-title">AI Reasoning</div>
          <div style={{
            fontSize: '0.82rem',
            color: 'var(--text-secondary)',
            lineHeight: 1.6,
            padding: 'var(--space-md)',
            background: 'var(--bg-glass)',
            borderRadius: 'var(--border-radius-xs)',
            border: '1px solid rgba(139, 92, 246, 0.2)',
          }}>
            {risk.llm_reasoning}
          </div>
        </div>
      )}

      {/* View Full Detail */}
      <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}
              onClick={() => onViewDetail(risk.risk_id)}>
        View Full Risk Detail →
      </button>
    </div>
  );
}
