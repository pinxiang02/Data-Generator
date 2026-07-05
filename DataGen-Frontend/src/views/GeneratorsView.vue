<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">Generators</h1>
      <button @click="openCreateModal" class="apple-btn-primary">Add Generator</button>
    </div>

<div class="apple-card" style="padding: 0; overflow: hidden;">
  <table class="apple-table" style="width: 100%; border-collapse: collapse; table-layout: fixed;">
    <thead>
      <tr>
        <th style="text-align: left; width: 5%; padding: 12px;">ID</th>
        <th style="text-align: center; width: 15%; padding: 12px;">Name</th>
        <th style="text-align: center; width: 20%; padding: 12px;">Description</th>
        <th style="text-align: center; width: 20%; padding: 12px;">Engine</th>
        <th style="text-align: center; width: 10%; padding: 12px;">Nodes</th>
        <th style="text-align: center; width: 10%; padding: 12px;">Actions</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="gen in generators" :key="gen.id" style="border-top: 1px solid var(--border-subtle);">
        <td style="color: var(--text-secondary); padding: 12px;">#{{ gen.id }}</td>
        <td style="font-weight: 500; padding: 12px; text-align: center;">{{ gen.name }}</td>
        <td style="color: var(--text-secondary); padding: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: center;">
          {{ gen.description || '--' }}
        </td>

        <td style="text-align: center; padding: 12px;">
          <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
            <span class="status-badge" :class="isRunning(gen.id) ? 'is-running' : 'is-idle'">
              <span class="status-led"></span>
              {{ isRunning(gen.id) ? 'Running' : 'Idle' }}
              <span v-if="msgCount(gen.id)" class="status-count">· {{ msgCount(gen.id) }} msgs</span>
            </span>
            <div class="engine-buttons" style="display: inline-flex; gap: 8px;">
              <button @click="startEngine(gen.id)" class="apple-btn-success small-btn">Start</button>
              <button @click="stopEngine(gen.id)" class="apple-btn-danger small-btn">Stop</button>
            </div>
          </div>
        </td>
        <td style="text-align: center; padding: 12px;">
          <router-link :to="`/generators/${gen.id}/nodes`" class="node-link">Configure</router-link>
        </td>
        <td style="text-align: center; padding: 12px;">
          <button @click="editGenerator(gen)" class="action-text-btn edit-color">Edit</button>
          <button @click="removeGenerator(gen.id)" class="action-text-btn delete-color" style="margin-left: 15px;">Delete</button>
        </td>
      </tr>
      
      <tr v-if="generators.length === 0">
        <td colspan="6" style="text-align: center; padding: 40px; color: var(--text-secondary);">No generators found.</td>
      </tr>
    </tbody>
  </table>
</div>

    <div v-if="showModal" class="modal-overlay">
      <div class="apple-card modal-content">
        <h2 style="margin-bottom: 20px;">{{ isEditing ? 'Edit Generator' : 'Create New Generator' }}</h2>
        <form @submit.prevent="submitGenerator">
          <div style="margin-bottom: 15px;">
            <label style="display: block; font-size: 14px; color: var(--text-secondary); margin-bottom: 5px;">Name</label>
            <input v-model="form.name" type="text" required class="apple-input" />
          </div>
          <div style="margin-bottom: 25px;">
            <label style="display: block; font-size: 14px; color: var(--text-secondary); margin-bottom: 5px;">Description</label>
            <input v-model="form.description" type="text" class="apple-input" />
          </div>
          <div style="display: flex; justify-content: flex-end; gap: 10px;">
            <button type="button" @click="closeModal" class="apple-btn-secondary">Cancel</button>
            <button type="submit" class="apple-btn-primary">{{ isEditing ? 'Save Changes' : 'Create' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import api from '../services/api';

const generators = ref([]);
const showModal = ref(false);
const isEditing = ref(false);
const editId = ref(null);
const status = ref({});   // { [genId]: { running, count } }
let statusTimer = null;

const form = ref({ name: '', description: '' });

const isRunning = (id) => !!status.value[id]?.running;
const msgCount = (id) => status.value[id]?.count || 0;

const loadStatus = async () => {
  try { status.value = (await api.getGeneratorsStatus()).data; }
  catch (error) { /* ignore transient status errors */ }
};

const loadGenerators = async () => {
  try { const response = await api.getGenerators(); generators.value = response.data; }
  catch (error) { console.error(error); }
};

const openCreateModal = () => {
  isEditing.value = false;
  form.value = { name: '', description: '' };
  showModal.value = true;
};

const editGenerator = (gen) => {
  isEditing.value = true;
  editId.value = gen.id;
  form.value = { name: gen.name, description: gen.description || '' };
  showModal.value = true;
};

const closeModal = () => { showModal.value = false; };

const submitGenerator = async () => {
  try {
    if (isEditing.value) { await api.updateGenerator(editId.value, form.value); } 
    else { await api.createGenerator(form.value); }
    closeModal();
    loadGenerators();
  } catch (error) { console.error(error); alert("Ensure backend endpoints are updated."); }
};

const removeGenerator = async (id) => {
  if(confirm("Are you sure? This deletes the generator and all nodes.")) {
    try { await api.deleteGenerator(id); loadGenerators(); } catch (error) { console.error(error); }
  }
};

const startEngine = async (id) => { try { await api.startGenerator(id); await loadStatus(); } catch (e) { alert(e.response?.data?.detail || "Error starting"); } };
const stopEngine = async (id) => { try { await api.stopGenerator(id); await loadStatus(); } catch (e) { alert(e.response?.data?.detail || "Error stopping"); } };

onMounted(() => {
  loadGenerators();
  loadStatus();
  statusTimer = setInterval(loadStatus, 2000);  // live running/count indicator
});
onUnmounted(() => clearInterval(statusTimer));
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 980px;
}
.status-led { width: 7px; height: 7px; border-radius: 50%; }
.status-badge.is-running { background: rgba(52, 199, 89, 0.15); color: #30d158; }
.status-badge.is-running .status-led { background: #34c759; box-shadow: 0 0 6px #34c759; }
.status-badge.is-idle { background: var(--surface-2); color: var(--text-secondary); }
.status-badge.is-idle .status-led { background: var(--text-secondary); }
.status-count { opacity: 0.85; }
</style>