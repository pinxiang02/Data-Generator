<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">API Destinations</h1>
      <button @click="showModal = true" class="apple-btn-primary">Add API Target</button>
    </div>

    <div class="apple-card" style="padding: 0; overflow: hidden;">
      <table class="apple-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Target URL</th>
            <th>Method</th>
            <th>Custom Header</th>
            <th style="text-align: right;">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="apis.length === 0">
            <td colspan="6" class="empty-state">No API targets configured.</td>
          </tr>
          <tr v-for="apiItem in apis" :key="apiItem.APIid">
            <td style="color: #86868b;">#{{ apiItem.APIid }}</td>
            <td style="font-weight: 500;">{{ apiItem.APIName }}</td>
            <td class="font-mono">{{ apiItem.TargetUrl }}</td>
            <td><span class="badge">{{ apiItem.Method }}</span></td>
            <td>
              <span v-if="apiItem.HeaderName">{{ apiItem.HeaderName }}: {{ apiItem.HeaderValue }}</span>
              <span v-else style="color: #86868b;">--</span>
            </td>
            <td>
              <div class="table-actions" style="justify-content: flex-end;">
                <button @click="editApi(apiItem)" class="action-btn edit-color">Edit</button>
                <button @click="deleteApi(apiItem.APIid)" class="action-btn delete-color">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content slide-down">
        <div class="modal-header">
          <h2 class="modal-title">{{ isEditing ? 'Edit API Destination' : 'New API Destination' }}</h2>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>API Name</label>
            <input v-model="form.APIName" type="text" class="apple-input" placeholder="e.g., Production DB">
          </div>
          <div class="form-group">
            <label>Target URL</label>
            <input v-model="form.TargetUrl" type="text" class="apple-input" placeholder="https://api.example.com/ingest">
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Method</label>
              <select v-model="form.Method" class="apple-input">
                <option>POST</option>
                <option>PUT</option>
                <option>PATCH</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Header Name (Optional)</label>
              <input v-model="form.HeaderName" type="text" class="apple-input" placeholder="Authorization">
            </div>
            <div class="form-group">
              <label>Header Value</label>
              <input v-model="form.HeaderValue" type="text" class="apple-input" placeholder="Bearer token...">
            </div>
          </div>
        </div>
        <div class="modal-footer modal-actions">
          <button @click="closeModal" class="apple-btn apple-btn-secondary">Cancel</button>
          <button @click="submitApi" class="apple-btn-primary">{{ isEditing ? 'Save Changes' : 'Save Target' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '../services/api';

const apis = ref([]);
const showModal = ref(false);
const isEditing = ref(false);
const editId = ref(null);

const form = ref({
  APIName: '',
  TargetUrl: '',
  Method: 'POST',
  HeaderName: '',
  HeaderValue: ''
});

const loadApis = async () => {
  try {
    const response = await api.getApis();
    apis.value = response.data;
  } catch (error) {
    console.error("Failed to load APIs:", error);
  }
};

const submitApi = async () => {
  if (!form.value.APIName || !form.value.TargetUrl) {
    alert("Name and URL are required.");
    return;
  }
  try {
    if (isEditing.value) {
      await api.updateApi(editId.value, form.value);
    } else {
      await api.createApi(form.value);
    }
    closeModal();
    loadApis();
  } catch (error) {
    console.error("Failed to save API target:", error);
  }
};

const editApi = (apiItem) => {
  isEditing.value = true;
  editId.value = apiItem.APIid;
  // Clone the data so typing doesn't instantly change the table text
  form.value = {
    APIName: apiItem.APIName,
    TargetUrl: apiItem.TargetUrl,
    Method: apiItem.Method,
    HeaderName: apiItem.HeaderName || '',
    HeaderValue: apiItem.HeaderValue || ''
  };
  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
  isEditing.value = false;
  editId.value = null;
  form.value = { APIName: '', TargetUrl: '', Method: 'POST', HeaderName: '', HeaderValue: '' };
};

const deleteApi = async (id) => {
  if (confirm("Delete this API target?")) {
    try {
      await api.deleteApi(id);
      loadApis();
    } catch (error) {
      console.error("Failed to delete API:", error);
    }
  }
};

onMounted(loadApis);
</script>