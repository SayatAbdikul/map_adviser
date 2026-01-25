import { createClient } from '@supabase/supabase-js';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    throw new Error('Missing Supabase environment variables');
}

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

/**
 * Example: Fetch data from a table
 */
export async function fetchPlaces(limit: number = 10) {
    const { data, error } = await supabase
        .from('places')
        .select('*')
        .limit(limit);

    if (error) {
        console.error('Error fetching places:', error);
        return [];
    }
    return data;
}

/**
 * Example: Insert a new record
 */
export async function insertPlace(place: {
    name: string;
    latitude: number;
    longitude: number;
    description?: string;
}) {
    const { data, error } = await supabase
        .from('places')
        .insert([place])
        .select();

    if (error) {
        console.error('Error inserting place:', error);
        return null;
    }
    return data[0];
}

/**
 * Example: Subscribe to real-time updates
 */
export function subscribeToPlaces(callback: (payload: unknown) => void) {
    return supabase
        .channel('places')
        .on(
            'postgres_changes',
            { event: '*', schema: 'public', table: 'places' },
            callback
        )
        .subscribe();
}
