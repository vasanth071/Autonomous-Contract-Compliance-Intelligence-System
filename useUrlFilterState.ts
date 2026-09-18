import { useSearchParams } from 'react-router-dom';

export function useUrlFilterState() {
  const [searchParams, setSearchParams] = useSearchParams();

  const docId = searchParams.get('doc') || 'all';
  const priority = searchParams.get('priority') || '';
  const sort = searchParams.get('sort') || 'deadline';

  const updateFilters = (newFilters: { doc?: string; priority?: string; sort?: string }) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      
      if (newFilters.doc !== undefined) {
        if (newFilters.doc === 'all' || !newFilters.doc) next.delete('doc');
        else next.set('doc', newFilters.doc);
      }
      
      if (newFilters.priority !== undefined) {
        if (!newFilters.priority) next.delete('priority');
        else next.set('priority', newFilters.priority);
      }
      
      if (newFilters.sort !== undefined) {
        if (newFilters.sort === 'deadline') next.delete('sort');
        else next.set('sort', newFilters.sort);
      }
      
      return next;
    }, { replace: true });
  };

  return { docId, priority, sort, updateFilters };
}
