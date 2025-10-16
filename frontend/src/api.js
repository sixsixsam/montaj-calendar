import axios from 'axios';

const API = axios.create({ 
  baseURL: process.env.REACT_APP_API_URL || 'https://montaj-calendar.onrender.com/api', 
  withCredentials: true 
});

// --- Auth ---
export const login = (username, password) => API.post('/auth/login', { username, password });
export const refresh = () => API.post('/auth/refresh');

// --- Calendar ---
export const getCalendar = (from, to, token) =>
  API.get(`/calendar?from_date=${from}&to_date=${to}`, { headers: { Authorization: `Bearer ${token}` } });

// --- Workers ---
export const getWorkers = (token) => API.get('/workers', { headers: { Authorization: `Bearer ${token}` } });
export const createUser = (token, payload) => API.post('/users', payload, { headers: { Authorization: `Bearer ${token}` } });
export const listUsers = (token) => API.get('/users', { headers: { Authorization: `Bearer ${token}` } });

// --- Projects ---
export const getProjects = (token) => API.get('/projects', { headers: { Authorization: `Bearer ${token}` } });

// --- Assignments ---
export const createAssignment = (token, payload) => API.post('/assignments', payload, { headers: { Authorization: `Bearer ${token}` } });
export const deleteAssignment = (token, id) => API.delete(`/assignments/${id}`, { headers: { Authorization: `Bearer ${token}` } });
export const listAssignments = (token, params) =>
  API.get('/assignments', { headers: { Authorization: `Bearer ${token}` }, params });

// --- Admin ---
export const resetPassword = (token, user_id, new_password) =>
  API.post('/admin/reset-password', null, { headers: { Authorization: `Bearer ${token}` }, params: { user_id, new_password } });
export const setRole = (token, user_id, role) =>
  API.post('/admin/set-role', null, { headers: { Authorization: `Bearer ${token}` }, params: { user_id, role } });

// --- Reports ---
export const exportWorkerReport = (token, worker_id, from, to) =>
  API.get(`/reports/worker?worker_id=${worker_id}&from_date=${from}&to_date=${to}`, { headers: { Authorization: `Bearer ${token}` }, responseType: 'blob' });
export const exportProjectsReport = (token, from, to) =>
  API.get(`/reports/projects?from_date=${from}&to_date=${to}`, { headers: { Authorization: `Bearer ${token}` }, responseType: 'blob' });
