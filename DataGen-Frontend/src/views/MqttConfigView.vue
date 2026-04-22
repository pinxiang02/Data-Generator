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

const form = ref({
  MQTTName: '',
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
  if (!form.value.MQTTName || !form.value.Topic) {
    alert("Broker Name and Topic are required.");
    return;
  }
  try {
    await api.createMqtt(form.value);
    showModal.value = false;
    form.value = { MQTTName: '', Topic: '' };
    loadMqtts();
  } catch (error) {
    console.error("Failed to create MQTT config:", error);
  }
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

onMounted(loadMqtts);
</script>