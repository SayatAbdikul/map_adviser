// Mock data types
export interface Place {
  id: string;
  name: string;
  description: string;
  category: string;
  coordinates: [number, number];
  address: string;
}

const MOCK_PLACES: Place[] = [
  {
    id: '1',
    name: 'Awesome Coffee',
    description: 'Best coffee in town',
    category: 'cafe',
    coordinates: [55.7558, 37.6173],
    address: 'Tverskaya St, 1',
  },
  {
    id: '2',
    name: 'Burger King',
    description: 'Fast food restaurant',
    category: 'restaurant',
    coordinates: [55.7539, 37.6208],
    address: 'Manege Sq, 1',
  },
  {
    id: '3',
    name: 'GUM',
    description: 'Famous department store',
    category: 'shopping',
    coordinates: [55.7547, 37.6215],
    address: 'Red Square, 3',
  },
];

export const mapService = {
  searchPlaces: async (query: string): Promise<Place[]> => {
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 500));
    
    if (!query) return [];
    
    const lowerQuery = query.toLowerCase();
    return MOCK_PLACES.filter(place => 
      place.name.toLowerCase().includes(lowerQuery) || 
      place.description.toLowerCase().includes(lowerQuery) ||
      place.category.toLowerCase().includes(lowerQuery)
    );
  },

  getPlaceById: async (id: string): Promise<Place | undefined> => {
    await new Promise((resolve) => setTimeout(resolve, 300));
    return MOCK_PLACES.find(place => place.id === id);
  },
};
