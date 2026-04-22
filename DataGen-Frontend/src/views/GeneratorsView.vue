<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">Generators</h1>
      <button @click="openCreateModal" class="apple-btn-primary">Add Generator</button>
    </div>

    <div class="apple-card" style="padding: 0; overflow: hidden;">
      <table class="apple-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Description</th>
            <th>Engine</th>
            <th>Nodes</th>
            <th style="text-align: right;">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="gen in generators" :key="gen.id">
            <td style="color: #86868b;">#{{ gen.id }}</td>
            <td style="font-weight: 500;">{{ gen.name }}</td>
            <td style="color: #86868b;">{{ gen.description || '--' }}</td>
            <td>
              <div class="engine-buttons">
                <button @click="startEngine(gen.id)" class="apple-btn-success small-btn">Start</button>
                <button @click="stopEngine(gen.id)" class="apple-btn-danger small-btn">Stop</button>
              </div>
            </td>
            <td>
              <router-link :to="`/generators/${gen.id}/nodes`" class="node-link">⚙️ Configure</router-link>
            </td>
            <td style="text-align: right;">
              <button @click="editGenerator(gen)" class="action-text-btn edit-color">Edit</button>
              <button @click="removeGenerator(gen.id)" class="action-text-btn delete-color" style="margin-left: 15px;">Delete</button>
            </td>
          </tr>
          <tr v-if="generators.length === 0">
            <td colspan="6" style="text-align: center; padding: 40px; color: #86868b;">No generators found. Click "Add Generator" to start.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="modal-overlay">
      <div class="apple-card modal-content">
        <h2 style="margin-bottom: 20px;">{{ isEditing ? 'Edit Generator' : 'Create New Generator' }}</h2>
        <form @submit.prevent="submitGenerator">
          <div style="margin-bottom: 15px;">
            <label style="display: block; font-size: 14px; color: #86868b; margin-bottom: 5px;">Name</label>
            <input v-model="form.name" type="text" required class="apple-input" />
          </div>
          <div style="margin-bottom: 25px;">
            <label style="display: block; font-size: 14px; color: #86868b; margin-bottom: 5px;">Description</label>
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
import { ref, onMounted } from 'vue';
import api from '../services/api';

const generators = ref([]);
const showModal = ref(false);
const isEditing = ref(false);
const editId = ref(null);

const form = ref({ name: '', description: '' });

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

const startEngine = async (id) => { try { await api.startGenerator(id); alert("Started"); } catch (e) { alert("Error starting"); } };
const stopEngine = async (id) => { try { await api.stopGenerator(id); alert("Stopped"); } catch (e) { alert("Error stopping"); } };

onMounted(loadGenerators);
</script>