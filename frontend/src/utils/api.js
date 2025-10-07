import axios from 'axios';

const normalizeBaseUrl = (url) => {
  if (!url) {
    return 'http://localhost:8000';
  }
  return url.endsWith('/') ? url.slice(0, -1) : url;
};

const API_ROOT = `${normalizeBaseUrl(import.meta.env.VITE_API_URL)}/api`;

const client = axios.create({
  baseURL: API_ROOT,
  timeout: 15000,
});

export const fetchSummary = async () => {
  const { data } = await client.get('/summary');
  return data;
};

export const fetchPlayers = async (params = {}) => {
  const { data } = await client.get('/players', { params });
  return data;
};

export const fetchPlayer = async (playerId) => {
  const { data } = await client.get(`/players/${playerId}`);
  return data;
};

export const fetchTeams = async (params = {}) => {
  const { data } = await client.get('/teams', { params });
  return data;
};

export const fetchTeam = async (teamId) => {
  const { data } = await client.get(`/teams/${teamId}`);
  return data;
};

export const triggerScrape = async (payload = { mode: 'test' }) => {
  const { data } = await client.post('/scrape', payload);
  return data;
};

export default client;
