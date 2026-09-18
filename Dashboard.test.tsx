import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import Dashboard from '../Dashboard';

// Mock API
vi.mock('../../api', () => ({
  getStats: vi.fn().mockResolvedValue({ total_documents: 2, total_risks: 2, pending_alerts: 0, risks_by_priority: { Critical: 1 } }),
  getRisks: vi.fn().mockResolvedValue({
    risks: [
      { risk_id: 'r1', doc_id: 'd1', priority_band: 'Critical', risk_type: 'gap', severity_score: 8, explanation: 'Risk 1' },
      { risk_id: 'r2', doc_id: 'd2', priority_band: 'Medium', risk_type: 'ambiguity', severity_score: 5, explanation: 'Risk 2' },
    ]
  }),
  getGraph: vi.fn().mockResolvedValue({ nodes: [], edges: [] }),
  getDocuments: vi.fn().mockResolvedValue([
    { doc_id: 'd1', filename: 'Doc 1' },
    { doc_id: 'd2', filename: 'Doc 2' }
  ])
}));

// Mock GraphViewer to avoid d3 issues in tests
vi.mock('../../components/GraphViewer', () => ({
  default: () => <div data-testid="mock-graph">Graph</div>
}));

describe('Dashboard', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/');
  });

  it('filters risks by both document and priority simultaneously', async () => {
    window.history.pushState({}, '', '/?doc=d1&priority=Critical');
    
    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );
    
    await waitFor(() => {
      expect(screen.queryByText('Risk 1...')).toBeInTheDocument();
      expect(screen.queryByText('Risk 2...')).not.toBeInTheDocument();
    });
  });

  it('shows empty state when no risks match the filter', async () => {
    window.history.pushState({}, '', '/?doc=d2&priority=Critical');
    
    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );
    
    await waitFor(() => {
      expect(screen.getByText('No risks found for this document/priority combination.')).toBeInTheDocument();
    });
  });
});
