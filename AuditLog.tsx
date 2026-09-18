import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getAuditLog, getDocuments, AuditEntry, DocumentInfo } from '../api';

export default function AuditLog() {
  const { docId } = useParams();
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<string>(docId || '');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDocuments().then(docs => {
      setDocuments(docs);
      if (!selectedDoc && docs.length > 0) {
        setSelectedDoc(docs[0].doc_id);
      }
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedDoc) return;
    setLoading(true);
    getAuditLog(selectedDoc).then(data => {
      setEntries(data.entries || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [selectedDoc]);

  return (
    <div className="fade-in">
      <div className="page-header" style={{ marginBottom: 'var(--space-md)' }}>
        <h2>Audit Trails</h2>
        <p>Complete evidence and reasoning chain for every AI decision</p>
      </div>

      <div className="filters-bar" style={{ background: 'var(--bg-card)', padding: 'var(--space-md)', borderRadius: 'var(--border-radius)', border: '1px solid var(--border-glass)', display: 'flex', alignItems: 'center', gap: 16 }}>
        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 600 }}>TARGET DOCUMENT</span>
        <select className="form-select" style={{ flex: 1, maxWidth: 400, fontWeight: 600 }} value={selectedDoc} onChange={e => setSelectedDoc(e.target.value)}>
          {documents.map(doc => (
            <option key={doc.doc_id} value={doc.doc_id}>
              {doc.doc_type === 'contract' ? '📑' : '📏'} {doc.filename} (v{doc.version})
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="loading-spinner"><div className="spinner" /></div>
      ) : entries.length === 0 ? (
        <div className="empty-state" style={{ marginTop: 'var(--space-2xl)' }}>
          <div className="empty-icon">📝</div>
          <p>No audit entries for this document.</p>
        </div>
      ) : (
        <div className="glass-card" style={{ marginTop: 'var(--space-lg)' }}>
          <div className="audit-timeline">
            {entries.map((entry, i) => (
              <div key={entry.log_id} className={`audit-entry stage-${entry.stage}`}
                   style={{ animationDelay: `${i * 50}ms` }}>
                <div className="audit-entry-header" style={{ marginBottom: 8 }}>
                  <span className="audit-stage-badge" style={{ padding: '4px 12px', fontSize: '0.7rem' }}>
                    {entry.stage}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                    {entry.created_at ? new Date(entry.created_at).toLocaleString() : ''}
                  </span>
                </div>
                
                <div style={{
                  background: 'var(--bg-glass)',
                  border: '1px solid var(--border-glass)',
                  padding: 'var(--space-md)',
                  borderRadius: 'var(--border-radius-xs)',
                  marginLeft: 4
                }}>
                  <div className="audit-reasoning" style={{ fontSize: '0.9rem', color: 'var(--text-primary)', fontWeight: 500 }}>
                    {entry.model_reasoning}
                  </div>
                  
                  {entry.output_json && (
                    <details style={{ marginTop: 12 }}>
                      <summary style={{ 
                        fontSize: '0.75rem', 
                        color: 'var(--accent-blue)', 
                        cursor: 'pointer',
                        fontWeight: 600,
                        userSelect: 'none'
                      }}>
                        View Model Payload
                      </summary>
                      <div style={{ 
                        marginTop: 8, 
                        background: '#020617', 
                        padding: 12, 
                        borderRadius: 6,
                        border: '1px solid #1e293b'
                      }}>
                        <pre style={{
                          fontSize: '0.72rem',
                          color: '#38bdf8',
                          overflow: 'auto',
                          maxHeight: 250,
                          margin: 0
                        }}>
                          {(() => {
                            try { return JSON.stringify(JSON.parse(entry.output_json), null, 2); } catch { return entry.output_json; }
                          })()}
                        </pre>
                      </div>
                    </details>
                  )}
                  {entry.input_hash && (
                    <div style={{ marginTop: 12, fontSize: '0.65rem', color: 'var(--text-dim)', fontFamily: 'monospace' }}>
                      <span style={{ opacity: 0.6 }}>INPUT_HASH:</span> {entry.input_hash}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
