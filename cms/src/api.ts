import axios from 'axios';

const API_URL = '/api';

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// Auth
export const login = (email: string, password: string) =>
  api.post('/auth/login', { email, password });

export const getMe = () => api.get('/auth/me');

// Shows
export const getShows = (params: Record<string, any>) =>
  api.get('/admin/shows', { params });

export const getShow = (id: string) =>
  api.get(`/admin/shows/${id}`);

export const createShow = (data: any) =>
  api.post('/admin/shows', data);

export const updateShow = (id: string, data: any) =>
  api.patch(`/admin/shows/${id}`, data);

export const deleteShow = (id: string) =>
  api.delete(`/admin/shows/${id}`);

// Seasons
export const getSeasons = (showId: string) =>
  api.get(`/admin/shows/${showId}/seasons`);

export const createSeason = (showId: string, data: any) =>
  api.post(`/admin/shows/${showId}/seasons`, data);

// Episodes
export const getEpisodes = (seasonId: string) =>
  api.get(`/admin/seasons/${seasonId}/episodes`);

export const createEpisode = (seasonId: string, data: any) =>
  api.post(`/admin/seasons/${seasonId}/episodes`, data);

export const updateEpisode = (id: string, data: any) =>
  api.patch(`/admin/episodes/${id}`, data);

export const deleteEpisode = (id: string) =>
  api.delete(`/admin/episodes/${id}`);

// Artwork
export const uploadShowArtwork = (showId: string, artworkType: string, file: File) => {
  const formData = new FormData();
  formData.append('artwork_type', artworkType);
  formData.append('file', file);
  return api.post(`/admin/shows/${showId}/artwork`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const uploadEpisodeArtwork = (episodeId: string, artworkType: string, file: File) => {
  const formData = new FormData();
  formData.append('artwork_type', artworkType);
  formData.append('file', file);
  return api.post(`/admin/episodes/${episodeId}/artwork`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

// Validation
export const getValidationReport = () =>
  api.get('/admin/validation-report');

// Publishing
export const publishCatalogue = () =>
  api.post('/admin/catalog/publish');

export const getPublishRuns = () =>
  api.get('/admin/publish-runs');
