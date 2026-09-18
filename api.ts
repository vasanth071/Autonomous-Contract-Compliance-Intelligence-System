import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
});

// ── Types ─────────────────────────────────────────────────────────────
export interface Stats {
  total_documents: number;
  total_risks: number;
  pending_alerts: number;
  risks_by_priority: Record<string, number>;
}

export interface DocumentInfo {
  doc_id: string;
  filename: string;
  doc_type: string;
  status: string;
  parties: string[];
  effective_date: string | null;
  version: string;
  error_msg: string | null;
  created_at: string;
}

export interface EvidenceEntry {
  label: string;
  doc_id: string;
  page: number | null;
  clause_id: string | null;
  text: string;
}

export interface Risk {
  risk_id: string;
  obligation_id: string | null;
  requirement_id: string | null;
  relationship_id: string | null;
  doc_id: string;
  risk_type: string;
  severity_score: number;
  priority_band: string;
  financial_exposure: number | null;
  financial_source: string;
  regulatory_severity: number;
  deadline_urgency: number;
  counterparty_importance: number;
  counterparty_source: string;
  explanation: string;
  evidence_trail: EvidenceEntry[];
  llm_reasoning: string | null;
  created_at: string;
  obligation?: Obligation;
  requirement?: Requirement;
  relationship?: Relationship;
}

export interface Obligation {
  obligation_id: string;
  chunk_id: string;
  doc_id: string;
  statement: string;
  responsible_party: string | null;
  deadline: string | null;
  trigger_condition: string | null;
  obligation_type: string | null;
  financial_exposure: number | null;
  counterparty_tier: string | null;
  extraction_confidence: number;
  field_status: Record<string, string>;
  source_evidence: { doc_id: string; page?: number; clause_id?: string; text_span: string };
  created_at: string;
}

export interface Requirement {
  requirement_id: string;
  chunk_id: string;
  doc_id: string;
  rule: string;
  scope: string | null;
  mandatory: boolean;
  extraction_confidence: number;
  field_status: Record<string, string>;
  source_evidence: { doc_id: string; page?: number; clause_id?: string; text_span: string };
  created_at: string;
}

export interface Relationship {
  relationship_id: string;
  edge_type: string;
  confidence: number;
  explanation: string;
  evidence_a: string;
  evidence_b: string;
}

export interface Alert {
  alert_id: string;
  risk_id: string;
  doc_id: string;
  owner_tag: string | null;
  priority_band: string;
  message: string;
  action_required: string | null;
  evidence_refs: EvidenceEntry[];
  acknowledged: boolean;
  created_at: string;
  risk?: Risk;
  obligation?: Obligation;
  requirement?: Requirement;
}

export interface AuditEntry {
  log_id: string;
  document_version: string;
  stage: string;
  entity_id: string | null;
  input_hash: string | null;
  output_json: string | null;
  model_reasoning: string | null;
  created_at: string;
}

export interface GraphData {
  nodes: { id: string; label: string; node_type: string; doc_id: string }[];
  edges: { source: string; target: string; edge_type: string; confidence: number; explanation?: string }[];
}

// ── API calls ─────────────────────────────────────────────────────────

export const getStats = () => api.get<Stats>('/stats').then(r => r.data);

export const getDocuments = () => api.get<DocumentInfo[]>('/documents').then(r => r.data);

export const getDocument = (id: string) => api.get<DocumentInfo & { chunks: unknown[] }>(`/documents/${id}`).then(r => r.data);

export const deleteDocument = (id: string) => api.delete(`/documents/${id}`).then(r => r.data);

export const uploadDocument = (file: File, docType: string) => {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('doc_type', docType);
  return api.post('/documents/upload', fd, { timeout: 0 }).then(r => r.data);
};

export const getRisks = (params?: Record<string, string>) =>
  api.get<{ total: number; risks: Risk[] }>('/risks', { params }).then(r => r.data);

export const getRiskDetail = (id: string) => api.get<Risk>(`/risks/${id}`).then(r => r.data);

export const getAlerts = (params?: Record<string, string>) =>
  api.get<{ total: number; alerts: Alert[] }>('/alerts', { params }).then(r => r.data);

export const getAlertEvidence = (id: string) => api.get<Alert>(`/alerts/${id}/evidence`).then(r => r.data);

export const getAuditLog = (docId: string) =>
  api.get<{ doc_id: string; entries: AuditEntry[] }>(`/audit/${docId}`).then(r => r.data);

export const getGraph = () => api.get<GraphData>('/mapping/graph').then(r => r.data);

export const getObligations = (params?: Record<string, string>) =>
  api.get<Obligation[]>('/obligations', { params }).then(r => r.data);

export const getRequirements = (params?: Record<string, string>) =>
  api.get<Requirement[]>('/requirements', { params }).then(r => r.data);

export default api;
