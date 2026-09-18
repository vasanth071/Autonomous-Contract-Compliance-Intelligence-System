import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import { uploadDocument, getDocuments, deleteDocument, DocumentInfo } from '../api';
import { useEffect } from 'react';

const PIPELINE_STAGES = ['Uploaded', 'Parsing', 'Extracting', 'Mapping', 'Detecting', 'Done'];

const STATUS_MAP: Record<string, number> = {
  uploaded: 0, parsing: 1, extracting: 2, mapping: 3, detecting: 4, done: 5, error: -1,
};

export default function Upload() {
  const navigate = useNavigate();
  const [docType, setDocType] = useState('contract');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ doc_id: string; filename: string } | null>(null);
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null);

  useEffect(() => {
    getDocuments().then(setDocuments).catch(() => {});
  }, []);

  // Poll for pipeline status
  useEffect(() => {
    if (!result) return;
    const interval = setInterval(async () => {
      try {
        const docs = await getDocuments();
        setDocuments(docs);
        const doc = docs.find(d => d.doc_id === result.doc_id);
        if (doc && (doc.status === 'done' || doc.status === 'error')) {
          clearInterval(interval);
        }
      } catch {
        // ignore
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [result]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;
    const file = acceptedFiles[0];
    setUploading(true);
    setError(null);
    try {
      const res = await uploadDocument(file, docType);
      setResult({ doc_id: res.doc_id, filename: res.filename });
      // Refresh doc list
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }, [docType]);

  const handleDelete = async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    try {
      await deleteDocument(docId);
      if (result?.doc_id === docId) {
        setResult(null);
      }
      if (expandedDoc === docId) {
        setExpandedDoc(null);
      }
      setDocuments(docs => docs.filter(d => d.doc_id !== docId));
    } catch (err) {
      console.error('Failed to delete document', err);
      alert('Failed to delete document');
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    },
    maxFiles: 1,
  });

  const currentDoc = result ? documents.find(d => d.doc_id === result.doc_id) : null;
  const currentStage = currentDoc ? STATUS_MAP[currentDoc.status] ?? -1 : -1;

  const getRelativeTime = (dateStr: string) => {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>Upload Documents</h2>
        <p>Upload contracts or policy documents for compliance analysis</p>
      </div>

      <div className="two-col">
        {/* Upload Zone */}
        <div className="glass-card">
          <div className="glass-card-header">
            <span className="glass-card-title">New Document</span>
          </div>

          <div style={{ marginBottom: 'var(--space-lg)' }}>
            <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 8 }}>
              Document Type
            </label>
            <select className="form-select" value={docType} onChange={e => setDocType(e.target.value)} style={{ width: '100%' }}>
              <option value="contract">📑 Contract</option>
              <option value="policy">📏 Policy / Regulatory Document</option>
            </select>
          </div>

          <div {...getRootProps()} className={`upload-zone ${isDragActive ? 'active' : ''}`}>
            <input {...getInputProps()} />
            <div className="upload-icon">{uploading ? '⏳' : '📁'}</div>
            {uploading ? (
              <p>Uploading...</p>
            ) : isDragActive ? (
              <p>Drop the file here</p>
            ) : (
              <>
                <p>Drag & drop a PDF or DOCX file here</p>
                <div className="upload-hint">or click to select a file</div>
              </>
            )}
          </div>

          {error && (
            <div style={{ marginTop: 'var(--space-md)', padding: 'var(--space-md)', background: 'var(--critical-bg)', borderRadius: 'var(--border-radius-xs)', color: 'var(--critical)', fontSize: '0.82rem', border: '1px solid var(--critical-border)' }}>
              ❌ {error}
            </div>
          )}

          {result && currentDoc && (
            <div style={{ marginTop: 'var(--space-lg)' }}>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 600, marginBottom: 'var(--space-sm)' }}>
                {currentDoc.filename}
              </div>

              {/* Pipeline Progress */}
              <div className="pipeline-progress" style={{ flexWrap: 'wrap' }}>
                {PIPELINE_STAGES.map((stage, i) => {
                  let cls = 'waiting';
                  if (currentDoc.status === 'error') {
                    cls = i <= Math.max(currentStage, 0) ? 'done' : 'waiting';
                    if (i === Math.max(currentStage + 1, 1)) cls = 'active';
                  } else if (i < currentStage) cls = 'done';
                  else if (i === currentStage) cls = currentDoc.status === 'done' ? 'done' : 'active';

                  return (
                    <div key={stage} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div className={`pipeline-step ${cls}`}>
                        {cls === 'done' ? '✅' : cls === 'active' ? '⏳' : '⬜'} {stage}
                      </div>
                      {i < PIPELINE_STAGES.length - 1 && <div className="pipeline-connector" />}
                    </div>
                  );
                })}
              </div>

              {currentDoc.status === 'error' && (
                <div style={{ marginTop: 'var(--space-md)', padding: 'var(--space-md)', background: 'var(--critical-bg)', borderRadius: 'var(--border-radius-xs)', color: 'var(--critical)', fontSize: '0.82rem', border: '1px solid var(--critical-border)' }}>
                  ❌ Pipeline error: {currentDoc.error_msg || 'Unknown error'}
                </div>
              )}

              {currentDoc.status === 'done' && (
                <div style={{ marginTop: 'var(--space-md)', padding: 'var(--space-md)', background: 'var(--low-bg)', borderRadius: 'var(--border-radius-xs)', color: 'var(--low)', fontSize: '0.82rem', border: '1px solid var(--low-border)' }}>
                  ✅ Analysis complete. View results on the Dashboard.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Recent Documents */}
        <div className="glass-card">
          <div className="glass-card-header">
            <span className="glass-card-title">Recent Documents</span>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>{documents.length} files</span>
          </div>
          {documents.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📂</div>
              <p>No documents uploaded yet</p>
            </div>
          ) : (
            <div className="doc-list">
              {documents.map(doc => (
                <div key={doc.doc_id} className={`doc-card ${expandedDoc === doc.doc_id ? 'expanded' : ''}`}>
                  <div className="doc-card-main" onClick={() => setExpandedDoc(expandedDoc === doc.doc_id ? null : doc.doc_id)}>
                    <div className="doc-card-icon">
                      {doc.doc_type === 'contract' ? '📑' : '📏'}
                    </div>
                    <div className="doc-card-info">
                      <div className="doc-card-name">{doc.filename}</div>
                      <div className="doc-card-meta">
                        <span className={`priority-badge ${doc.status === 'done' ? 'low' : doc.status === 'error' ? 'critical' : 'medium'}`} style={{ fontSize: '0.6rem', padding: '2px 8px' }}>
                          {doc.status}
                        </span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                          {getRelativeTime(doc.created_at)}
                        </span>
                      </div>
                    </div>
                    <div className="doc-card-chevron">{expandedDoc === doc.doc_id ? '▲' : '▼'}</div>
                  </div>
                  {expandedDoc === doc.doc_id && (
                    <div className="doc-card-details">
                      <div className="doc-detail-row">
                        <span className="doc-detail-label">Type</span>
                        <span className="doc-detail-value">{doc.doc_type}</span>
                      </div>
                      <div className="doc-detail-row">
                        <span className="doc-detail-label">Version</span>
                        <span className="doc-detail-value">v{doc.version}</span>
                      </div>
                      {doc.parties && doc.parties.length > 0 && (
                        <div className="doc-detail-row">
                          <span className="doc-detail-label">Parties</span>
                          <span className="doc-detail-value">{doc.parties.join(', ')}</span>
                        </div>
                      )}
                      {doc.effective_date && (
                        <div className="doc-detail-row">
                          <span className="doc-detail-label">Effective</span>
                          <span className="doc-detail-value">{new Date(doc.effective_date).toLocaleDateString()}</span>
                        </div>
                      )}
                      <div className="doc-detail-row">
                        <span className="doc-detail-label">Uploaded</span>
                        <span className="doc-detail-value">{new Date(doc.created_at).toLocaleString()}</span>
                      </div>
                      <div className="doc-card-actions">
                        <a className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '6px 12px', textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }} href={`http://localhost:8000/api/documents/${doc.doc_id}/download`} target="_blank" rel="noreferrer">
                          📄 View Document
                        </a>
                        <button className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '6px 12px' }} onClick={() => navigate(`/audit/${doc.doc_id}`)}>
                          📝 View Audit Trail
                        </button>
                        <button className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '6px 12px' }} onClick={() => navigate('/dashboard')}>
                          📊 Dashboard
                        </button>
                        <button className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '6px 12px', color: 'var(--critical)' }} onClick={(e) => handleDelete(doc.doc_id, e)}>
                          🗑️ Delete
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
