import React from 'react';
import type { Place } from '@/services/mapService';
import { Card } from '@/components/common/Card';
import { MapPin } from 'lucide-react';

interface SearchResultsProps {
  results: Place[];
  onSelect: (place: Place) => void;
}

export const SearchResults: React.FC<SearchResultsProps> = ({ results, onSelect }) => {
  if (results.length === 0) return null;

  return (
    <div className="mt-2 space-y-2 max-h-[60vh] overflow-y-auto">
      {results.map((place) => (
        <Card 
          key={place.id}
          className="cursor-pointer hover:bg-[color:var(--app-surface-2)] transition-colors"
          onClick={() => onSelect(place)}
        >
          <div className="flex items-start">
            <MapPin className="text-[color:var(--app-accent)] mt-1 flex-shrink-0" size={18} />
            <div className="ml-3">
              <h3 className="font-medium app-text">{place.name}</h3>
              <p className="text-sm app-muted">{place.address}</p>
              <span className="inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium bg-[color:var(--app-surface-2)] text-[color:var(--app-muted)]">
                {place.category}
              </span>
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
};
