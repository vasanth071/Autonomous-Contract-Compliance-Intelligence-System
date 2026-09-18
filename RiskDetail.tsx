import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getRiskDetail, Risk } from '../api';

export default function RiskDetail() {
  const { riskId } = useParams();
  const navigate = useNavigate();
  const [risk, setRisk] = useState<Risk | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!riskId) return;
    getRiskDetail(riskId).then(r => {
      setRisk(r);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [riskId]);

  if (loading) return <div className="loading-spinner"><div className="spinner" /></div>;
  if (!risk) return <div className="empty-state"><div className="empty-icon">🔍</div><p>Risk not found</p></div>;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
          <button className="btn btn-ghost" onClick={() => navigate('/')}>← Back</button>
          <div>
            <h2>Risk Detail</h2>
            <p style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
              <span className={`priority-badge ${risk.priority_band.toLowerCase()}`}>{risk.priority_band}</span>
              <span className={`risk-type-badge ${risk.risk_type}`}>{risk.risk_type.replace('_', ' ')}</span>
              <span style={{ color: 'var(--text-muted)' }}>Score: {risk.severity_score.toFixed(1)}</span>
            </p>
          </div>
        </div>
      </div>

      {/* Risk Explanation */}
      <div className={`glass-card alert-detail-card ${risk.priority_band.toLowerCase()}`}>
        <div className="alert-message">{risk.explanation}</div>
        {risk.llm_reasoning && (
          <div className="alert-action">
            <strong>AI Reasoning:</strong> {risk.llm_reasoning}
          </div>
        )}
      </div>

      <div className="two-col">
        {/* Obligation */}
        {risk.obligation && (
          <div className="glass-card">
            <div className="glass-card-header">
              <span className="glass-card-title">📑 Contract Obligation</span>
              <div className="confidence-bar" style={{ width: 80 }}>
                <div className="confidence-fill" style={{ width: `${risk.obligation.extraction_confidence * 100}%` }} />
              </div>
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.6, marginBottom: 'var(--space-md)' }}>
              {risk.obligation.statement}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-md)', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              {risk.obligation.responsible_party && (
                <div><strong>Responsible:</strong> {risk.obligation.responsible_party}</div>
              )}
              {risk.obligation.deadline && (
                <div><strong>Deadline:</strong> {risk.obligation.deadline}</div>
              )}
              {risk.obligation.obligation_type && (
                <div><strong>Type:</strong> {risk.obligation.obligation_type}</div>
              )}
            </div>
            {/* Field Status */}
            <div style={{ marginTop: 'var(--space-md)', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {Object.entries(risk.obligation.field_status).map(([field, status]) => (
                <span key={field} className={`source-badge ${status === 'present' ? 'extracted' : 'estimated'}`}>
                  {field}: {status}
                </span>
              ))}
            </div>
            {/* Source Evidence */}
            <div className="evidence-quote contract" style={{ marginTop: 'var(--space-md)' }}>
              {risk.obligation.source_evidence?.text_span}
              <div className="evidence-citation">
                📄 Page {risk.obligation.source_evidence?.page}, Clause {risk.obligation.source_evidence?.clause_id}
              </div>
            </div>
          </div>
        )}

        {/* Requirement */}
        {risk.requirement && (
          <div className="glass-card">
            <div className="glass-card-header">
              <span className="glass-card-title">📏 Policy Requirement</span>
              <div className="confidence-bar" style={{ width: 80 }}>
                <div className="confidence-fill" style={{ width: `${risk.requirement.extraction_confidence * 100}%` }} />
              </div>
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.6, marginBottom: 'var(--space-md)' }}>
              {risk.requirement.rule}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-md)', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              {risk.requirement.scope && (
                <div><strong>Scope:</strong> {risk.requirement.scope}</div>
              )}
              <div><strong>Mandatory:</strong> {risk.requirement.mandatory ? '✅ Yes' : '⬜ No'}</div>
            </div>
            <div style={{ marginTop: 'var(--space-md)', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {Object.entries(risk.requirement.field_status).map(([field, status]) => (
                <span key={field} className={`source-badge ${status === 'present' ? 'extracted' : 'estimated'}`}>
                  {field}: {status}
                </span>
              ))}
            </div>
            <div className="evidence-quote policy" style={{ marginTop: 'var(--space-md)' }}>
              {risk.requirement.source_evidence?.text_span}
              <div className="evidence-citation">
                📄 Page {risk.requirement.source_evidence?.page}, Clause {risk.requirement.source_evidence?.clause_id}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Relationship */}
      {risk.relationship && (
        <div className="glass-card" style={{ marginTop: 'var(--space-lg)' }}>
          <div className="glass-card-header">
            <span className="glass-card-title">🔗 Relationship Analysis</span>
            <span className={`risk-type-badge ${risk.relationship.edge_type}`}>
              {risk.relationship.edge_type}
            </span>
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 'var(--space-md)' }}>
            {risk.relationship.explanation}
          </div>
          <div className="confidence-bar" style={{ marginBottom: 'var(--space-md)' }}>
            <div className="confidence-fill" style={{ width: `${risk.relationship.confidence * 100}%` }} />
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Confidence: {(risk.relationship.confidence * 100).toFixed(0)}%
          </div>
        </div>
      )}

      {/* Scoring Breakdown */}
      <div className="glass-card" style={{ marginTop: 'var(--space-lg)' }}>
        <div className="glass-card-header">
          <span className="glass-card-title">📊 Scoring Breakdown</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-md)' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {risk.financial_exposure != null ? `$${risk.financial_exposure.toLocaleString()}` : 'N/A'}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>
              Financial Exposure
              <span className={`source-badge ${risk.financial_source}`} style={{ marginLeft: 4 }}>
                {risk.financial_source}
              </span>
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {risk.regulatory_severity.toFixed(1)}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>Regulatory Severity</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {risk.deadline_urgency.toFixed(1)}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>Deadline Urgency</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {risk.counterparty_importance.toFixed(1)}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>
              Counterparty
              <span className={`source-badge ${risk.counterparty_source}`} style={{ marginLeft: 4 }}>
                {risk.counterparty_source}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Evidence Trail */}
      {risk.evidence_trail && risk.evidence_trail.length > 0 && (
        <div className="glass-card" style={{ marginTop: 'var(--space-lg)' }}>
          <div className="glass-card-header">
            <span className="glass-card-title">📋 Evidence Trail</span>
          </div>
          {risk.evidence_trail.map((ev, i) => (
            <div key={i} className={`evidence-quote ${ev.label.toLowerCase().includes('contract') ? 'contract' : 'policy'}`}
                 style={{ marginBottom: 'var(--space-md)' }}>
              <strong>{ev.label}</strong>
              <div style={{ marginTop: 6 }}>{ev.text}</div>
              <div className="evidence-citation">
                {ev.page && `Page ${ev.page}`} {ev.clause_id && `· Clause ${ev.clause_id}`}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
