import React, { useState, useEffect } from 'react';
import { Search, X } from 'lucide-react';
import { useDebounce } from '@/hooks/useDebounce'; // We need to create this hook
import { Input } from '@/components/common/Input';
import { mapService } from '@/services/mapService';
import type { Place } from '@/services/mapService';

interface SearchBarProps {
  onResults: (results: Place[]) => void;
  onClear: () => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({ onResults, onClear }) => {
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    const search = async () => {
      if (!debouncedQuery.trim()) {
        onClear();
        return;
      }

      setIsLoading(true);
      try {
        const results = await mapService.searchPlaces(debouncedQuery);
        onResults(results);
      } catch (error) {
        console.error('Search failed:', error);
      } finally {
        setIsLoading(false);
      }
    };

    search();
  }, [debouncedQuery]);

  return (
    <div className="relative">
      <Input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search for places..."
        leftIcon={<Search size={18} />}
        rightIcon={
          query ? (
            <button onClick={() => setQuery('')} className="text-gray-400 hover:text-gray-600">
              <X size={18} />
            </button>
          ) : undefined
        }
      />
      {isLoading && (
        <div className="absolute right-10 top-1/2 -translate-y-1/2">
           {/* Loader can go here if needed, but Input doesn't support generic right element yet properly besides icon */}
        </div>
      )}
    </div>
  );
};
