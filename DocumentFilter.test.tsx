import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import DocumentFilter from '../DocumentFilter';

describe('DocumentFilter', () => {
  const mockDocs = [
    { doc_id: '1', filename: 'contract.pdf' } as any,
    { doc_id: '2', filename: 'policy.docx' } as any,
  ];

  it('renders all options and selects the default', () => {
    render(<DocumentFilter documents={mockDocs} selectedDocId="all" onChange={vi.fn()} />);
    expect(screen.getByRole('combobox')).toHaveValue('all');
    expect(screen.getAllByRole('option')).toHaveLength(3); // "All Documents" + 2 docs
  });

  it('calls onChange when a document is selected', () => {
    const handleChange = vi.fn();
    render(<DocumentFilter documents={mockDocs} selectedDocId="all" onChange={handleChange} />);
    
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '2' } });
    expect(handleChange).toHaveBeenCalledWith('2');
  });
});
