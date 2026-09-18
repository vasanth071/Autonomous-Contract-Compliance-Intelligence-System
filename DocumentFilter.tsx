import React from 'react';
import type { DocumentInfo } from '../api';

interface Props {
  documents: DocumentInfo[];
  selectedDocId: string;
  onChange: (docId: string) => void;
}

export default function DocumentFilter({ documents, selectedDocId, onChange }: Props) {
  return (
    <select 
      className="form-select" 
      value={selectedDocId} 
      onChange={e => onChange(e.target.value)}
      aria-label="Filter by Document"
    >
      <option value="all">All Documents</option>
      {documents.map(doc => (
        <option key={doc.doc_id} value={doc.doc_id}>
          {doc.filename}
        </option>
      ))}
    </select>
  );
}
