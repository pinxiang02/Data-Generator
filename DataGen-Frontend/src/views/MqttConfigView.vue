<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">Message Brokers</h1>
      <button @click="showModal = true" class="apple-btn-primary">Add MQTT Config</button>
    </div>

    <div class="apple-card" style="padding: 0; overflow: hidden;">
      <table class="apple-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Broker Name</th>
            <th>Topic</th>
            <th style="text-align: right;">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="mqtts.length === 0">
            <td colspan="4" class="empty-state">No Message Brokers configured.</td>
          </tr>
          <tr v-for="mqtt in mqtts" :key="mqtt.MQTTid">
            <td style="color: #86868b;">#{{ mqtt.MQTTid }}</td>
            <td style="font-weight: 500;">{{ mqtt.MQTTName }}</td>
            <td class="font-mono"><span class="badge">{{ mqtt.Topic }}</span></td>
            <td>
              <div class="table-actions" style="justify-content: flex-end;">
                <button @click="editMqtt(mqtt)" class="action-btn edit-color">Edit</button>
                <button @click="deleteMqtt(mqtt.MQTTid)" class="action-btn delete-color">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal-content slide-down">
        <div class="modal-header">
          <h2 class="modal-title">New Message Broker</h2>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Broker Connection Name</label>
            <input v-model="form.MQTTName" type="text" class="apple-input" placeholder="e.g., NATS Jetstream Factory A">
          </div>
          
          <div class="form-row" style="display: flex; gap: 1rem; margin-bottom: 1rem;">
            <div class="form-group" style="flex: 2;">
              <label>Host / IP</label>
              <input v-model="form.Host" type="text" class="apple-input" placeholder="localhost">
            </div>
            <div class="form-group" style="flex: 1;">
              <label>Port</label>
              <input v-model="form.Port" type="number" class="apple-input" placeholder="1884">
            </div>
          </div>
          
          <div class="form-group">
            <label>Topic / Subject</label>
            <input v-model="form.Topic" type="text" class="apple-input" placeholder="telemetry.factory.line1">
          </div>
        </div>
        <div class="modal-footer modal-actions">
          <button @click="showModal = false" class="apple-btn apple-btn-secondary">Cancel</button>
          <button @click="submitMqtt" class="apple-btn-primary">Save Broker</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '../services/api';

const mqtts = ref([]);
const showModal = ref(false);

const isEditing = ref(false);
const editId = ref(null);

const form = ref({
  MQTTName: '',
  Host: 'localhost',
  Port: 1884,
  Topic: ''
});

const loadMqtts = async () => {
  try {
    const response = await api.getMqtts();
    mqtts.value = response.data;
  } catch (error) {
    console.error("Failed to load MQTT configs:", error);
  }
};

const submitMqtt = async () => {
  if (!form.value.MQTTName || !form.value.Topic || !form.value.Host || !form.value.Port) {
    alert("All fields are required.");
    return;
  }
  
  try {
    if (isEditing.value) {
      // If editing, send an update request to the backend
      await api.updateMqtt(editId.value, form.value);
    } else {
      // If not editing, create a new one
      await api.createMqtt(form.value);
    }
    
    closeModal();
    loadMqtts();
  } catch (error) {
    console.error("Failed to save MQTT config:", error);
  }
};

const editMqtt = (mqtt) => {
  isEditing.value = true;
  editId.value = mqtt.MQTTid;
  
  // Clone the data so typing doesn't instantly change the table text
  form.value = { 
    MQTTName: mqtt.MQTTName, 
    Host: mqtt.Host, 
    Port: mqtt.Port, 
    Topic: mqtt.Topic 
  };
  showModal.value = true;
};

const deleteMqtt = async (id) => {
  if (confirm("Delete this Message Broker configuration?")) {
    try {
      await api.deleteMqtt(id);
      loadMqtts();
    } catch (error) {
      console.error("Failed to delete MQTT config:", error);
    }
  }
};

const closeModal = () => {
  showModal.value = false;
  isEditing.value = false;
  editId.value = null;
  form.value = { MQTTName: '', Host: '127.0.0.1', Port: 1884, Topic: '' };
};

onMounted(loadMqtts);
</script>