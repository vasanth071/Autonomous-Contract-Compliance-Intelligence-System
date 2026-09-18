import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import AlertDetail from '../AlertDetail';

vi.mock('../../api', () => ({
  getDocuments: vi.fn().mockResolvedValue([
    { doc_id: 'd1', filename: 'Doc 1' }
  ]),
  getAlerts: vi.fn().mockResolvedValue({
    alerts: [
      { alert_id: 'a1', doc_id: 'd1', priority_band: 'High', message: 'Alert A', created_at: '2023-01-01', risk: { deadline_urgency: 2 } },
      { alert_id: 'a2', doc_id: 'd1', priority_band: 'Critical', message: 'Alert B', created_at: '2023-01-02', risk: { deadline_urgency: 5 } },
    ]
  }),
  getAlertEvidence: vi.fn().mockRejectedValue(new Error('not used'))
}));

describe('AlertDetail List View', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/');
  });

  it('sorts alerts by deadline urgency by default', async () => {
    render(
      <BrowserRouter>
        <AlertDetail />
      </BrowserRouter>
    );

    await waitFor(() => {
      const messages = screen.getAllByText(/Alert (A|B)/);
      // Alert B has higher deadline urgency
      expect(messages[0]).toHaveTextContent('Alert B');
      expect(messages[1]).toHaveTextContent('Alert A');
    });
  });

  it('sorts alerts by creation date when sort param is date', async () => {
    window.history.pushState({}, '', '/?sort=date');
    render(
      <BrowserRouter>
        <AlertDetail />
      </BrowserRouter>
    );

    await waitFor(() => {
      const messages = screen.getAllByText(/Alert (A|B)/);
      // Alert B is newer (2023-01-02 vs 2023-01-01)
      expect(messages[0]).toHaveTextContent('Alert B');
      expect(messages[1]).toHaveTextContent('Alert A');
    });
  });
  
  it('shows empty state when no alerts match document filter', async () => {
    window.history.pushState({}, '', '/?doc=d2');
    render(
      <BrowserRouter>
        <AlertDetail />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No alerts found for this combination of filters.')).toBeInTheDocument();
    });
  });
});
