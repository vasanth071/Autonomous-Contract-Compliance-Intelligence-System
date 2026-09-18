import { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getAlerts, getAlertEvidence, getDocuments, Alert, DocumentInfo } from '../api';
import DocumentFilter from '../components/DocumentFilter';
import { useUrlFilterState } from '../hooks/useUrlFilterState';

export default function AlertDetail() {
  const { alertId } = useParams();
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { docId, sort, updateFilters } = useUrlFilterState();

  useEffect(() => {
    Promise.all([
      getDocuments().catch(() => []),
      alertId ? Promise.resolve([]) : getAlerts().then(r => r.alerts || []).catch(() => []),
    ]).then(([docs, alts]) => {
      setDocuments(docs);
      if (alertId) {
        getAlertEvidence(alertId).then(a => {
          setSelectedAlert(a);
          setLoading(false);
        }).catch(err => {
          setError(err.response?.data?.detail || "Failed to load alert details. It may have been deleted.");
          setLoading(false);
        });
      } else {
        setAlerts(alts);
        setLoading(false);
      }
    }).catch(err => {
      setError("Failed to load data.");
      setLoading(false);
    });
  }, [alertId]);

  const docMap = useMemo(() => {
    return documents.reduce((acc, doc) => {
      acc[doc.doc_id] = doc;
      return acc;
    }, {} as Record<string, DocumentInfo>);
  }, [documents]);

  const filteredAndSortedGroups = useMemo(() => {
    const filtered = alerts.filter(a => docId === 'all' || a.doc_id === docId);

    const sorted = [...filtered].sort((a, b) => {
      if (sort === 'deadline') {
        return (b.risk?.deadline_urgency ?? 0) - (a.risk?.deadline_urgency ?? 0);
      }
      if (sort === 'date') {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
      if (sort === 'priority') {
        const p = { Critical: 4, High: 3, Medium: 2, Low: 1 };
        return (p[b.priority_band as keyof typeof p] ?? 0) - (p[a.priority_band as keyof typeof p] ?? 0);
      }
      return 0;
    });

    const groups: Record<string, Alert[]> = {};
    sorted.forEach(alert => {
      if (!groups[alert.doc_id]) groups[alert.doc_id] = [];
      groups[alert.doc_id].push(alert);
    });

    return Object.entries(groups).sort(([, a], [, b]) => {
      const ax = a[0], bx = b[0];
      if (sort === 'deadline') return (bx.risk?.deadline_urgency ?? 0) - (ax.risk?.deadline_urgency ?? 0);
      if (sort === 'date') return new Date(bx.created_at).getTime() - new Date(ax.created_at).getTime();
      if (sort === 'priority') {
        const p = { Critical: 4, High: 3, Medium: 2, Low: 1 };
        return (p[bx.priority_band as keyof typeof p] ?? 0) - (p[ax.priority_band as keyof typeof p] ?? 0);
      }
      return 0;
    });
  }, [alerts, docId, sort]);

  if (loading) return <div className="loading-spinner"><div className="spinner" /></div>;

  if (error) {
    return (
      <div className="fade-in">
        <div className="glass-card empty-state" style={{ marginTop: 'var(--space-2xl)' }}>
          <div className="empty-icon">⚠️</div>
          <p style={{ color: 'var(--critical)', fontSize: '1.1rem', marginBottom: 'var(--space-md)' }}>{error}</p>
          <button className="btn btn-primary" onClick={() => navigate('/alerts')}>Return to Alerts</button>
        </div>
      </div>
    );
  }

  // ── Single alert detail view ──
  if (selectedAlert && alertId) {
    const priorityBand = selectedAlert.priority_band || 'Low';
    return (
      <div className="fade-in">
        <div className="page-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
            <button className="btn btn-ghost" onClick={() => navigate('/alerts')}>← Back</button>
            <div>
              <h2>Alert Detail</h2>
              <p style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 4, flexWrap: 'wrap' }}>
                <span className={`priority-badge ${priorityBand.toLowerCase()}`}>
                  {priorityBand}
                </span>
                {selectedAlert.owner_tag && (
                  <span className="risk-type-badge">👤 {selectedAlert.owner_tag}</span>
                )}
                {docMap[selectedAlert.doc_id] && (
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    📄 {docMap[selectedAlert.doc_id].filename}
                  </span>
                )}
              </p>
            </div>
          </div>
        </div>

        <div className={`glass-card alert-detail-card ${priorityBand.toLowerCase()}`}>
          <div className="alert-message">{selectedAlert.message}</div>
          {selectedAlert.action_required && (
            <div className="alert-action">
              <strong>🎯 Recommended Action:</strong> {selectedAlert.action_required}
            </div>
          )}
        </div>

        {/* Evidence Chain — shows page/clause/line references */}
        {selectedAlert.evidence_refs && selectedAlert.evidence_refs.length > 0 && (
          <div className="glass-card" style={{ marginTop: 'var(--space-lg)' }}>
            <div className="glass-card-header">
              <span className="glass-card-title">📋 Evidence Chain</span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                {selectedAlert.evidence_refs.length} source{selectedAlert.evidence_refs.length > 1 ? 's' : ''}
              </span>
            </div>
            {selectedAlert.evidence_refs.map((ev, i) => {
              const evDoc = docMap[ev.doc_id];
              return (
                <div key={i} className={`evidence-quote ${ev.label.toLowerCase().includes('contract') ? 'contract' : 'policy'}`}
                     style={{ marginBottom: 'var(--space-md)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <strong style={{ fontSize: '0.8rem' }}>{ev.label}</strong>
                    {evDoc && (
                      <span className="risk-type-badge" style={{ fontSize: '0.62rem' }}>
                        {evDoc.doc_type === 'contract' ? '📑' : '📏'} {evDoc.filename}
                      </span>
                    )}
                  </div>
                  <div style={{ marginTop: 6, fontSize: '0.85rem', lineHeight: 1.7 }}>{ev.text}</div>
                  <div className="evidence-citation" style={{ display: 'flex', gap: 12, marginTop: 8 }}>
                    {ev.page != null && (
                      <span>📄 Page {ev.page}</span>
                    )}
                    {ev.clause_id && (
                      <span>📌 Clause {ev.clause_id}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Linked Risk */}
        {selectedAlert.risk && (
          <div className="glass-card" style={{ marginTop: 'var(--space-lg)' }}>
            <div className="glass-card-header">
              <span className="glass-card-title">⚠️ Linked Risk</span>
              <button className="btn btn-ghost" onClick={() => navigate(`/risks/${selectedAlert.risk!.risk_id}`)}>
                View Full Risk →
              </button>
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              {selectedAlert.risk.explanation}
            </div>
            {selectedAlert.risk.llm_reasoning && (
              <div className="alert-action" style={{ marginTop: 'var(--space-md)' }}>
                <strong>AI Reasoning:</strong> {selectedAlert.risk.llm_reasoning}
              </div>
            )}
            {/* Scoring mini-grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 'var(--space-sm)', marginTop: 'var(--space-md)' }}>
              {[
                { label: 'Score', value: selectedAlert.risk.severity_score != null ? selectedAlert.risk.severity_score.toFixed(1) : 'N/A' },
                { label: 'Regulatory', value: selectedAlert.risk.regulatory_severity != null ? selectedAlert.risk.regulatory_severity.toFixed(1) : 'N/A' },
                { label: 'Urgency', value: selectedAlert.risk.deadline_urgency != null ? selectedAlert.risk.deadline_urgency.toFixed(1) : 'N/A' },
                { label: 'Exposure', value: selectedAlert.risk.financial_exposure != null ? `$${selectedAlert.risk.financial_exposure.toLocaleString()}` : 'N/A' },
              ].map(item => (
                <div key={item.label} style={{ textAlign: 'center', padding: 'var(--space-sm)', background: 'var(--bg-glass)', borderRadius: 'var(--border-radius-xs)', border: '1px solid var(--border-glass)' }}>
                  <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>{item.value}</div>
                  <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', marginTop: 2, textTransform: 'uppercase' }}>{item.label}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Obligation & Requirement */}
        <div className="two-col" style={{ marginTop: 'var(--space-lg)' }}>
          {selectedAlert.obligation && (
            <div className="glass-card">
              <div className="glass-card-header">
                <span className="glass-card-title">📑 Contract Obligation</span>
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.6 }}>
                {selectedAlert.obligation.statement}
              </div>
              {selectedAlert.obligation.responsible_party && (
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: 'var(--space-sm)' }}>
                  <strong>Responsible:</strong> {selectedAlert.obligation.responsible_party}
                </div>
              )}
              {selectedAlert.obligation.deadline && (
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                  <strong>Deadline:</strong> {selectedAlert.obligation.deadline}
                </div>
              )}
              <div className="evidence-quote contract" style={{ marginTop: 'var(--space-md)' }}>
                {selectedAlert.obligation.source_evidence?.text_span}
                <div className="evidence-citation">
                  📄 Page {selectedAlert.obligation.source_evidence?.page}, Clause {selectedAlert.obligation.source_evidence?.clause_id}
                </div>
              </div>
            </div>
          )}
          {selectedAlert.requirement && (
            <div className="glass-card">
              <div className="glass-card-header">
                <span className="glass-card-title">📏 Policy Requirement</span>
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.6 }}>
                {selectedAlert.requirement.rule}
              </div>
              {selectedAlert.requirement.scope && (
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: 'var(--space-sm)' }}>
                  <strong>Scope:</strong> {selectedAlert.requirement.scope}
                </div>
              )}
              <div className="evidence-quote policy" style={{ marginTop: 'var(--space-md)' }}>
                {selectedAlert.requirement.source_evidence?.text_span}
                <div className="evidence-citation">
                  📄 Page {selectedAlert.requirement.source_evidence?.page}, Clause {selectedAlert.requirement.source_evidence?.clause_id}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── Alert list view ──
  return (
    <div className="fade-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div>
          <h2>Compliance Alerts</h2>
          <p>Actionable alerts with evidence-traceable citations</p>
        </div>
        <div className="controls-bar">
          <DocumentFilter
            documents={documents}
            selectedDocId={docId}
            onChange={(newDocId) => updateFilters({ doc: newDocId })}
          />
          <select
            className="form-select"
            value={sort}
            onChange={e => updateFilters({ sort: e.target.value })}
            aria-label="Sort By"
          >
            <option value="deadline">Sort by Deadline Urgency</option>
            <option value="priority">Sort by Priority</option>
            <option value="date">Sort by Creation Date</option>
          </select>
        </div>
      </div>

      {/* Summary ribbon */}
      <div className="alert-summary-ribbon">
        <div className="alert-summary-item">
          <span className="alert-summary-count">{alerts.length}</span>
          <span className="alert-summary-label">Total Alerts</span>
        </div>
        <div className="alert-summary-item">
          <span className="alert-summary-count" style={{ color: 'var(--critical)' }}>
            {alerts.filter(a => a.priority_band === 'Critical').length}
          </span>
          <span className="alert-summary-label">Critical</span>
        </div>
        <div className="alert-summary-item">
          <span className="alert-summary-count" style={{ color: 'var(--high)' }}>
            {alerts.filter(a => a.priority_band === 'High').length}
          </span>
          <span className="alert-summary-label">High</span>
        </div>
        <div className="alert-summary-item">
          <span className="alert-summary-count">
            {new Set(alerts.map(a => a.doc_id)).size}
          </span>
          <span className="alert-summary-label">Documents</span>
        </div>
      </div>

      {filteredAndSortedGroups.length === 0 ? (
        <div className="glass-card">
          <div className="empty-state">
            <div className="empty-icon">🔔</div>
            <p>No alerts found for this combination of filters.</p>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xl)' }}>
          {filteredAndSortedGroups.map(([groupDocId, docAlerts]) => {
            const doc = docMap[groupDocId];
            return (
              <div key={groupDocId} className="glass-card">
                <div className="glass-card-header" style={{ borderBottom: '1px solid var(--border-glass)', paddingBottom: 'var(--space-md)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{ fontSize: '1.6rem' }}>{doc?.doc_type === 'contract' ? '📑' : '📏'}</span>
                    <div>
                      <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {doc ? doc.filename : 'Unknown Document'}
                      </h3>
                      <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', gap: 12, marginTop: 2 }}>
                        <span>{docAlerts.length} active {docAlerts.length === 1 ? 'alert' : 'alerts'}</span>
                        {doc?.doc_type && <span>· {doc.doc_type}</span>}
                        {doc?.parties && doc.parties.length > 0 && <span>· {doc.parties.join(', ')}</span>}
                      </p>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', marginTop: 'var(--space-md)' }}>
                  {docAlerts.map(alert => (
                    <div key={alert.alert_id}
                         className={`alert-card ${alert.priority_band.toLowerCase()}`}
                         onClick={() => navigate(`/alerts/${alert.alert_id}`)}>
                      <div className="alert-card-header">
                        <span className={`priority-badge ${alert.priority_band.toLowerCase()}`}>
                          {alert.priority_band}
                        </span>
                        {alert.owner_tag && (
                          <span className="risk-type-badge">👤 {alert.owner_tag}</span>
                        )}
                        {alert.evidence_refs && alert.evidence_refs.length > 0 && alert.evidence_refs[0].page != null && (
                          <span className="risk-type-badge" style={{ fontSize: '0.62rem' }}>
                            📄 Page {alert.evidence_refs[0].page}
                            {alert.evidence_refs[0].clause_id && ` · ${alert.evidence_refs[0].clause_id}`}
                          </span>
                        )}
                        {alert.risk?.deadline_urgency != null && (
                          <span className="risk-type-badge">
                            ⏰ Urgency: {alert.risk.deadline_urgency.toFixed(1)}
                          </span>
                        )}
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginLeft: 'auto' }}>
                          {new Date(alert.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="alert-message">{alert.message}</div>
                      {alert.action_required && (
                        <div className="alert-action" style={{ marginTop: 'var(--space-sm)' }}>
                          🎯 {alert.action_required}
                        </div>
                      )}
                      {/* Evidence preview */}
                      {alert.evidence_refs && alert.evidence_refs.length > 0 && (
                        <div style={{ marginTop: 'var(--space-sm)', display: 'flex', gap: 'var(--space-sm)', flexWrap: 'wrap' }}>
                          {alert.evidence_refs.slice(0, 2).map((ev, idx) => (
                            <div key={idx} style={{ fontSize: '0.72rem', color: 'var(--text-dim)', background: 'var(--bg-glass)', padding: '4px 8px', borderRadius: 'var(--border-radius-xs)', border: '1px solid var(--border-glass)' }}>
                              {ev.label}{ev.page != null ? ` · p.${ev.page}` : ''}{ev.clause_id ? ` · ${ev.clause_id}` : ''}
                            </div>
                          ))}
                          {alert.evidence_refs.length > 2 && (
                            <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)', alignSelf: 'center' }}>+{alert.evidence_refs.length - 2} more</span>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
