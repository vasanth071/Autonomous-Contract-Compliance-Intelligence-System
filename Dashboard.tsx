import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { getStats, getRisks, getGraph, getDocuments, Stats, Risk, GraphData, DocumentInfo } from '../api';
import GraphViewer from '../components/GraphViewer';
import EvidencePanel from '../components/EvidencePanel';
import DocumentFilter from '../components/DocumentFilter';
import { useUrlFilterState } from '../hooks/useUrlFilterState';

const RISK_TYPE_DESCRIPTIONS: Record<string, string> = {
  policy_conflict: 'A clause in the contract directly contradicts a regulatory or policy requirement.',
  deadline_breach: 'An obligation deadline has passed or is at imminent risk of being missed.',
  ambiguity: 'Vague or unclear language that could be interpreted in conflicting ways.',
  gap: 'A required policy area has no corresponding contract coverage.',
  missing_coverage: 'An obligation exists without a matching policy requirement.',
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<Stats | null>(null);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [selectedRisk, setSelectedRisk] = useState<Risk | null>(null);
  const [loading, setLoading] = useState(true);
  const [hoveredBand, setHoveredBand] = useState<string | null>(null);
  
  const { docId, priority, updateFilters } = useUrlFilterState();

  useEffect(() => {
    Promise.all([
      getStats().catch(() => null),
      getRisks().catch(() => ({ risks: [] })),
      getGraph().catch(() => ({ nodes: [], edges: [] })),
      getDocuments().catch(() => []),
    ]).then(([s, r, g, docs]) => {
      setStats(s);
      setRisks(r.risks || []);
      setGraph(g);
      setDocuments(docs);
      setLoading(false);
    });
  }, []);

  const docMap = useMemo(() => {
    return documents.reduce((acc, doc) => {
      acc[doc.doc_id] = doc;
      return acc;
    }, {} as Record<string, DocumentInfo>);
  }, [documents]);

  const filteredRisks = risks.filter(r => {
    const docMatch = docId === 'all' || r.doc_id === docId;
    const prioMatch = !priority || r.priority_band === priority;
    return docMatch && prioMatch;
  });

  const bandRisks = useMemo(() => {
    if (!hoveredBand) return [];
    return risks.filter(r => r.priority_band === hoveredBand);
  }, [risks, hoveredBand]);

  if (loading) {
    return (
      <div className="loading-spinner">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Compliance Dashboard</h2>
        <p>Real-time contract compliance intelligence overview</p>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">📄</div>
          <div className="stat-value">{stats?.total_documents ?? 0}</div>
          <div className="stat-label">Documents Analysed</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">⚠️</div>
          <div className="stat-value">{stats?.total_risks ?? 0}</div>
          <div className="stat-label">Active Risks</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🔔</div>
          <div className="stat-value">{stats?.pending_alerts ?? 0}</div>
          <div className="stat-label">Pending Alerts</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🔴</div>
          <div className="stat-value">{stats?.risks_by_priority?.Critical ?? 0}</div>
          <div className="stat-label">Critical Risks</div>
        </div>
      </div>

      {/* Risk Ranking Table — full width */}
      <div className="glass-card" style={{ marginBottom: 'var(--space-lg)' }}>
        <div className="glass-card-header">
          <span className="glass-card-title">Risk Rankings</span>
          <div className="controls-bar">
            <DocumentFilter 
              documents={documents} 
              selectedDocId={docId} 
              onChange={(newDocId) => updateFilters({ doc: newDocId })} 
            />
            <select className="form-select" value={priority} onChange={e => updateFilters({ priority: e.target.value })}>
              <option value="">All Priorities</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
          </div>
        </div>
        <div className="data-table-wrapper">
          {filteredRisks.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <p>No risks found for this document/priority combination.</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Source Document</th>
                  <th>Risk Description</th>
                  <th>Type</th>
                  <th>Purpose</th>
                  <th>Priority</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {filteredRisks.map(risk => {
                  const doc = docMap[risk.doc_id];
                  return (
                    <tr key={risk.risk_id} onClick={() => setSelectedRisk(risk)}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ fontSize: '1rem' }}>{doc?.doc_type === 'contract' ? '📑' : '📏'}</span>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: '0.82rem' }}>{doc?.filename ?? 'Unknown'}</div>
                            <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>{doc?.doc_type ?? ''}</div>
                          </div>
                        </div>
                      </td>
                      <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {risk.explanation?.slice(0, 100)}...
                      </td>
                      <td>
                        <span className={`risk-type-badge ${risk.risk_type}`}>
                          {risk.risk_type.replace('_', ' ')}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', maxWidth: 200 }}>
                        {RISK_TYPE_DESCRIPTIONS[risk.risk_type] || 'Compliance risk detected'}
                      </td>
                      <td>
                        <span className={`priority-badge ${risk.priority_band.toLowerCase()}`}>
                          {risk.priority_band}
                        </span>
                      </td>
                      <td style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '1rem' }}>
                        {risk.severity_score.toFixed(1)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="two-col">
        {/* Graph Preview */}
        <div className="glass-card">
          <div className="glass-card-header">
            <span className="glass-card-title">Relationship Graph</span>
          </div>
          {graph && graph.nodes.length > 0 ? (
            <GraphViewer data={graph} onNodeClick={(id) => {
              const risk = risks.find(r => r.obligation_id === id || r.requirement_id === id);
              if (risk) navigate(`/risks/${risk.risk_id}`);
            }} />
          ) : (
            <div className="empty-state">
              <div className="empty-icon">🔗</div>
              <p>No graph data yet. Upload documents to see relationships.</p>
            </div>
          )}
        </div>

        {/* Priority Distribution — larger, interactive */}
        {stats && (
          <div className="glass-card">
            <div className="glass-card-header">
              <span className="glass-card-title">Risk Distribution</span>
            </div>
            <div className="risk-dist-chart">
              {(['Critical', 'High', 'Medium', 'Low'] as const).map(band => {
                const count = stats.risks_by_priority[band] ?? 0;
                const maxCount = Math.max(...Object.values(stats.risks_by_priority), 1);
                const barHeight = Math.max(12, (count / maxCount) * 180);
                const colors: Record<string, string> = {
                  Critical: 'var(--critical)',
                  High: 'var(--high)',
                  Medium: 'var(--medium)',
                  Low: 'var(--low)',
                };
                const isHovered = hoveredBand === band;
                return (
                  <div 
                    key={band} 
                    className={`risk-dist-col ${isHovered ? 'hovered' : ''}`}
                    onMouseEnter={() => setHoveredBand(band)}
                    onMouseLeave={() => setHoveredBand(null)}
                    onClick={() => updateFilters({ priority: band })}
                    style={{ cursor: 'pointer' }}
                  >
                    <div className="risk-dist-bar-wrapper">
                      <div className="risk-dist-bar" style={{
                        height: `${barHeight}px`,
                        background: `linear-gradient(to top, ${colors[band]}, ${colors[band]}88)`,
                        boxShadow: isHovered ? `0 0 20px ${colors[band]}66` : 'none',
                      }} />
                    </div>
                    <div className="risk-dist-count" style={{ color: colors[band] }}>
                      {count}
                    </div>
                    <div className="risk-dist-label">{band}</div>
                  </div>
                );
              })}
            </div>
            {/* Hover detail panel */}
            {hoveredBand && bandRisks.length > 0 && (
              <div className="risk-dist-detail">
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: 8 }}>
                  {hoveredBand} Risks ({bandRisks.length})
                </div>
                {bandRisks.slice(0, 3).map(r => (
                  <div key={r.risk_id} className="risk-dist-detail-item" onClick={() => setSelectedRisk(r)}>
                    <span className={`risk-type-badge ${r.risk_type}`} style={{ fontSize: '0.65rem' }}>
                      {r.risk_type.replace('_', ' ')}
                    </span>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {r.explanation?.slice(0, 60)}...
                    </span>
                    <span style={{ fontWeight: 700, fontSize: '0.82rem' }}>{r.severity_score.toFixed(1)}</span>
                  </div>
                ))}
                {bandRisks.length > 3 && (
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: 4 }}>
                    +{bandRisks.length - 3} more
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Evidence Panel */}
      <div className={`overlay ${selectedRisk ? 'visible' : ''}`} onClick={() => setSelectedRisk(null)} />
      <EvidencePanel
        risk={selectedRisk}
        onClose={() => setSelectedRisk(null)}
        onViewDetail={(id) => navigate(`/risks/${id}`)}
      />
    </div>
  );
}
