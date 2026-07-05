import axios from 'axios';
import router from '../router';

const TOKEN_KEY = 'datagen-token';
const USER_KEY = 'datagen-username';

export const auth = {
  get token() { return localStorage.getItem(TOKEN_KEY); },
  get username() { return localStorage.getItem(USER_KEY); },
  get isAuthenticated() { return !!localStorage.getItem(TOKEN_KEY); },
  set(token, username) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, username);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
};

const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  headers: { 'Content-Type': 'application/json' },
});

// Attach the bearer token to every request when present.
apiClient.interceptors.request.use((config) => {
  const t = auth.token;
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

// On 401 (expired/invalid token) log out and bounce to the login page.
apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response && error.response.status === 401 && auth.isAuthenticated) {
      auth.clear();
      if (router.currentRoute.value.name !== 'Login') {
        router.push({ name: 'Login' });
      }
    }
    return Promise.reject(error);
  }
);

export default {
  // --- Auth ---
  signup(username, password) { return apiClient.post('/auth/signup', { username, password }); },
  login(username, password) { return apiClient.post('/auth/login', { username, password }); },
  me() { return apiClient.get('/auth/me'); },

  // --- Generators CRUD ---
  getGenerators() { return apiClient.get('/generators/'); },
  getGeneratorsStatus() { return apiClient.get('/generators/status'); },
  createGenerator(data) { return apiClient.post(`/generators/?name=${encodeURIComponent(data.name)}&desc=${encodeURIComponent(data.description || '')}`); },
  updateGenerator(id, data) { return apiClient.put(`/generators/${id}`, data); },
  deleteGenerator(id) { return apiClient.delete(`/generators/${id}`); },

  // --- Engine Controls ---
  startGenerator(id) { return apiClient.post(`/generators/${id}/start`, { target_api_id: null, target_mqtt_id: null }); },
  stopGenerator(id) { return apiClient.post(`/generators/${id}/stop`); },

  // --- Nodes CRUD ---
  getNodesForGenerator(generatorId) { return apiClient.get(`/generators/${generatorId}/nodes/`); },
  createNode(generatorId, data) { return apiClient.post(`/generators/${generatorId}/nodes/`, data); },
  updateNode(generatorId, nodeId, data) { return apiClient.put(`/generators/${generatorId}/nodes/${nodeId}`, data); },
  deleteNode(generatorId, nodeId) { return apiClient.delete(`/generators/${generatorId}/nodes/${nodeId}`); },

  startEngine(id, targetApiId = null, targetMqttId = null, targetDbId = null) {
    return apiClient.post(`/generators/${id}/start`, {
      target_api_id: targetApiId,
      target_mqtt_id: targetMqttId,
      target_db_id: targetDbId,
    });
  },
  stopEngine(id) { return apiClient.post(`/generators/${id}/stop`); },
  getTelemetry(id) { return apiClient.get(`/generators/${id}/telemetry?t=${Date.now()}`); },

  // --- API Configuration ---
  getApis() { return apiClient.get('/apis/'); },
  createApi(data) { return apiClient.post('/apis/', data); },
  updateApi(id, data) { return apiClient.put(`/apis/${id}`, data); },
  deleteApi(id) { return apiClient.delete(`/apis/${id}`); },

  // --- MQTT Configuration ---
  getMqtts() { return apiClient.get('/mqtt/'); },
  createMqtt(data) { return apiClient.post('/mqtt/', data); },
  updateMqtt(id, data) { return apiClient.put(`/mqtt/${id}`, data); },
  deleteMqtt(id) { return apiClient.delete(`/mqtt/${id}`); },

  // --- Database Configuration (PostgreSQL sink) ---
  getDatabases() { return apiClient.get('/databases/'); },
  createDatabase(data) { return apiClient.post('/databases/', data); },
  updateDatabase(id, data) { return apiClient.put(`/databases/${id}`, data); },
  deleteDatabase(id) { return apiClient.delete(`/databases/${id}`); },
  testDatabase(data) { return apiClient.post('/databases/test', data); },
  getDatabaseSchema(id) { return apiClient.get(`/databases/${id}/schema`); },
  generateGeneratorFromDatabase(id) { return apiClient.post(`/databases/${id}/generate-generator`); },
};
