import axios from 'axios';

const API_URL = '/api';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

export interface Episode {
  id: string;
  title: string;
  duration: number | null;
  content_group: string;
  languages: string[];
  thumbnail: string;
}

export interface Season {
  number: number;
  episodes: Episode[];
}

export interface Trailer {
  id: string;
  title: string;
  duration: number | null;
  language: string;
  thumbnail: string;
}

export interface Show {
  id: string;
  title: string;
  synopsis: string;
  category: string;
  poster: string;
  banner: string;
  thumbnail: string;
  seasons: Season[];
  trailers?: Trailer[];
}

export interface Section {
  name: string;
  shows: Show[];
}

export interface CatalogResponse {
  version: string;
  published_at: string | null;
  sections: Section[];
}

export interface SearchResult {
  show: Show;
  section: string;
}

export interface SearchResponse {
  query: string | null;
  filters: {
    category: string | null;
    language: string | null;
    section: string | null;
  };
  results: SearchResult[];
  total: number;
}

// Viewer reads ONLY published catalog and search endpoints
export const getCatalog = async (): Promise<CatalogResponse> => {
  const res = await api.get<CatalogResponse>('/catalog');
  return res.data;
};

export const searchCatalog = async (params: {
  q?: string;
  category?: string;
  language?: string;
  section?: string;
}): Promise<SearchResponse> => {
  const res = await api.get<SearchResponse>('/catalog/search', { params });
  return res.data;
};

export default api;
