import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000', 
  headers: {
    'Content-Type': 'application/json'
  }
});

export default {
  // --- Generators CRUD ---
  getGenerators() { return apiClient.get('/generators/'); },
  createGenerator(data) { return apiClient.post(`/generators/?name=${data.name}&desc=${data.description}`); },
  
  // NEW: Update Generator
  updateGenerator(id, data) { return apiClient.put(`/generators/${id}?name=${data.name}&desc=${data.description}`); },
  
  deleteGenerator(id) { return apiClient.delete(`/generators/${id}`); },
  
  // --- Engine Controls ---
  startGenerator(id) { return apiClient.post(`/generators/${id}/start`); },
  stopGenerator(id) { return apiClient.post(`/generators/${id}/stop`); },

  // --- Nodes CRUD ---
  getNodesForGenerator(generatorId) { return apiClient.get(`/generators/${generatorId}/nodes/`); },
  createNode(generatorId, data) { return apiClient.post(`/generators/${generatorId}/nodes/`, data); },
  deleteNode(generatorId, nodeId) { return apiClient.delete(`/generators/${generatorId}/nodes/${nodeId}`); },

  startEngine(id, targetApiId = null) {
    return apiClient.post(`/generators/${id}/start`, {
      target_api_id: targetApiId
    });
  },
  stopEngine(id) {
    return apiClient.post(`/generators/${id}/stop`);
  },
  getTelemetry(id) {
    // The timestamp (?t=...) prevents the browser from caching old data
    return apiClient.get(`/generators/${id}/telemetry?t=${Date.now()}`);
  },

  // --- API Configuration Methods ---
  getApis() { return apiClient.get('/apis/'); },
  createApi(data) { return apiClient.post('/apis/', data); },
  deleteApi(id) { return apiClient.delete(`/apis/${id}`); },

  // --- MQTT Configuration Methods ---
  getMqtts() { return apiClient.get('/mqtt/'); },
  createMqtt(data) { return apiClient.post('/mqtt/', data); },
  deleteMqtt(id) { return apiClient.delete(`/mqtt/${id}`); },
};