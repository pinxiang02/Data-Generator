<template>
  <div class="page-container wide-container">
    <button @click="$router.back()" class="back-btn">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" style="margin-right: 6px;">
        <path fill-rule="evenodd" d="M11.354 1.646a.5.5 0 0 1 0 .708L5.707 8l5.647 5.646a.5.5 0 0 1-.708.708l-6-6a.5.5 0 0 1 0-.708l6-6a.5.5 0 0 1 .708 0z"/>
      </svg>
      Back to Generators
    </button>
    
    <div class="page-header">
      <h1 class="page-title">Configure Engine <span class="engine-id-badge">ID: {{ id }}</span></h1>
      <div class="engine-controls">
        <button @click="startEngine" class="apple-btn apple-btn-success">▶ Start Engine</button>
        <button @click="stopEngine" class="apple-btn apple-btn-danger">■ Stop</button>
      </div>
    </div>

    <div class="split-layout">
      <div class="left-panel">
        
        <div class="apple-card config-section">
          <h2 class="section-heading">Destination Settings</h2>
          <div class="toggle-group">
            
            <label class="apple-toggle-label">
              <input type="checkbox" v-model="generator.is_api_enabled" @change="updateSettings">
              <span>Enable API Destination</span>
            </label>

            <div v-if="generator.is_api_enabled" style="margin-left: 28px; margin-top: 4px; margin-bottom: 8px;">
              <select v-model="selectedApiId" class="apple-input" style="padding: 6px 10px; font-size: 13px; width: 100%; max-width: 250px;">
                <option :value="null">-- Select API Target --</option>
                <option v-for="apiItem in availableApis" :key="apiItem.APIid" :value="apiItem.APIid">
                  {{ apiItem.APIName }}
                </option>
              </select>
            </div>

            <label class="apple-toggle-label">
              <input type="checkbox" v-model="generator.is_message_broker_enabled" @change="updateSettings">
              <span>Enable Message Broker (MQTT/NATS)</span>
            </label>
            
            <div v-if="generator.is_message_broker_enabled" style="margin-left: 28px; margin-top: 4px; margin-bottom: 8px;">
              <select v-model="selectedMqttId" class="apple-input" style="padding: 6px 10px; font-size: 13px; width: 100%; max-width: 250px;">
                <option :value="null">-- Select MQTT Broker --</option>
                <option v-for="mqttItem in availableMqtts" :key="mqttItem.MQTTid" :value="mqttItem.MQTTid">
                  {{ mqttItem.MQTTName }}
                </option>
              </select>
            </div>
            
          </div>
        </div>

        <div class="apple-card config-section">
          <h2 class="section-heading">{{ isEditingNode ? 'Edit Node' : 'Add New Node' }}</h2>
          <form @submit.prevent="submitNode" class="node-form">
            <div class="form-group">
              <label>Node Name (JSON Key)</label>
              <input type="text" v-model="form.node_name" class="apple-input" required placeholder="e.g., temperature" />
            </div>
            
            <div class="form-row">
              <div class="form-group">
                <label>Data Type</label>
                <select v-model="form.data_type_enum" class="apple-input">
                  <option value="String">String</option>
                  <option value="Integer">Integer</option>
                  <option value="Float">Float</option>
                  <option value="Boolean">Boolean</option>
                </select>
              </div>
              <div class="form-group">
                <label>Generation Mode</label>
                <select v-model="form.generation_mode" class="apple-input">
                  <option value="Fixed">Fixed Value</option>
                  <option value="Random">Random Range</option>
                  <option value="List">List Selection</option>
                </select>
              </div>
            </div>

            <div v-if="form.generation_mode === 'Fixed'" class="form-group slide-down">
              <label>Fixed Value</label>
              <input type="text" v-model="form.fixed_value" class="apple-input" placeholder="Value to always return" />
            </div>

            <div v-if="form.generation_mode === 'Random'" class="form-row slide-down">
              <div class="form-group">
                <label>Min Range</label>
                <input type="number" step="any" v-model="form.min_range" class="apple-input" placeholder="0" />
              </div>
              <div class="form-group">
                <label>Max Range</label>
                <input type="number" step="any" v-model="form.max_range" class="apple-input" placeholder="100" />
              </div>
            </div>

            <div v-if="form.generation_mode === 'List'" class="form-group slide-down">
              <label>Value List (Comma separated)</label>
              <input type="text" v-model="form.value_list" class="apple-input" placeholder="apple, banana, orange" />
            </div>

            <div class="form-actions">
              <button v-if="isEditingNode" type="button" @click="cancelEdit" class="apple-btn apple-btn-secondary">Cancel</button>
              <button type="submit" class="apple-btn apple-btn-primary">{{ isEditingNode ? 'Save Changes' : 'Add Node' }}</button>
            </div>
          </form>
        </div>

        <div class="apple-card">
          <h2 class="section-heading">Configured Nodes</h2>
          <div v-if="nodes.length === 0" class="empty-state">
            No nodes configured yet. Add one above.
          </div>
          <table v-else class="apple-table">
            <thead>
              <tr>
                <th>Key Name</th>
                <th>Type</th>
                <th>Mode</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="node in nodes" :key="node.id">
                <td class="font-mono">{{ node.node_name }}</td>
                <td><span class="badge">{{ node.data_type_enum }}</span></td>
                <td>{{ node.generation_mode }}</td>
                <td class="table-actions">
                  <button @click="editNode(node)" class="action-btn edit-color">Edit</button>
                  <button @click="removeNode(node.id)" class="action-btn delete-color">Del</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>

      <div class="right-panel">
        
        <div class="console-wrapper">
          <div class="console-header">
            <div class="window-controls">
              <span class="status-dot pulsing"></span>
              <span class="status-dot yellow"></span>
              <span class="status-dot green"></span>
            </div>
            <h3>Live Payload Output</h3>
          </div>
          <div class="console-body" ref="payloadConsole">
            <pre v-if="livePayloads.length === 0" class="placeholder-text">Awaiting engine start...</pre>
            <pre v-for="(log, idx) in livePayloads" :key="'payload-'+idx">{{ log }}</pre>
          </div>
        </div>

        <div class="console-wrapper">
          <div class="console-header">
            <div class="window-controls">
              <span class="status-dot"></span>
              <span class="status-dot"></span>
              <span class="status-dot"></span>
            </div>
            <h3>API Response Logs</h3>
          </div>
          <div class="console-body" ref="responseConsole">
            <pre v-if="liveResponses.length === 0" class="placeholder-text">Awaiting API responses...</pre>
            <pre v-for="(log, idx) in liveResponses" :key="'response-'+idx">{{ log }}</pre>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import { useRoute } from 'vue-router';
import api from '../services/api';

const isEditingNode = ref(false);
const isApiEnabled = ref(false);

const availableApis = ref([]);
const selectedApiId = ref(null);

const availableMqtts = ref([]);
const selectedMqttId = ref(null);

const route = useRoute();
const id = route.params.id;

const generator = ref({ is_api_enabled: false, is_message_broker_enabled: false });
const nodes = ref([]);
const livePayloads = ref([]); // PLURAL - Matches the template loop
const liveResponses = ref([]);

const form = ref({ node_name: '', data_type_enum: 'String', generation_mode: 'Fixed' });
const payloadConsole = ref(null);
const responseConsole = ref(null);
let pollingTimer = null;
let lastTimestamp = 0;

const scrollToBottom = async () => {
  await nextTick();
  if (payloadConsole.value) payloadConsole.value.scrollTop = payloadConsole.value.scrollHeight;
};

const startPolling = () => {
  pollingTimer = setInterval(async () => {
    try {
      const res = await api.getTelemetry(id);
      if (res.data && res.data.timestamp > lastTimestamp) {
        lastTimestamp = res.data.timestamp;
        
        // Update Payload Console
        livePayloads.value.push(JSON.stringify(res.data.data, null, 2));
        
        let addedLog = false;

        // Catch API Logs
        if (res.data.api_log) {
            liveResponses.value.push(`[API] ${res.data.api_log}`);
            addedLog = true;
        }
        
        // Catch MQTT Logs (NEW)
        if (res.data.mqtt_log) {
            liveResponses.value.push(`[MQTT] ${res.data.mqtt_log}`);
            addedLog = true;
        }
        
        if (addedLog) {
            if (liveResponses.value.length > 50) liveResponses.value.shift();
            nextTick(() => {
                // Ensure you have a ref="responseConsole" on this div in your template
                if (responseConsole.value) {
                    responseConsole.value.scrollTop = responseConsole.value.scrollHeight;
                }
            });
        }
        scrollToBottom();
      }
    } catch (e) { console.warn(e); }
  }, 1000);
};

const loadData = async () => {
  const genRes = await api.getGenerators();
  generator.value = genRes.data.find(g => g.id == id) || generator.value;
  const nodeRes = await api.getNodesForGenerator(id);
  nodes.value = nodeRes.data;
};

const startEngine = async () => {
  try {
    const apiIdToSend = generator.value.is_api_enabled ? selectedApiId.value : null;
    const mqttIdToSend = generator.value.is_message_broker_enabled ? selectedMqttId.value : null;

    // Send both IDs to the backend
    await api.startEngine(id, apiIdToSend, mqttIdToSend);
    
    livePayloads.value.push(`// Engine start signal sent (API: ${apiIdToSend || 'None'} | MQTT: ${mqttIdToSend || 'None'})...`);
    scrollToBottom();
  } catch (e) {
    const errorMsg = e.response?.data?.detail || e.message;
    livePayloads.value.push(`// Error: ${errorMsg}`);
  }
};

const stopEngine = async () => {
  try {
    await api.stopEngine(id);
    livePayloads.value.push("// Engine stop signal sent.");
    scrollToBottom();
  } catch (e) {
    const errorMsg = e.response?.data?.detail || e.message;
    livePayloads.value.push(`// Error: ${errorMsg}`);
  }
};

const loadApis = async () => {
  try {
    const res = await api.getApis(); 
    availableApis.value = res.data;
  } catch (error) {
    console.warn("Failed to load APIs", error);
  }
};

const loadMqtts = async () => {
  try {
    const res = await api.getMqtts(); 
    availableMqtts.value = res.data;
  } catch (error) {
    console.warn("Failed to load MQTTs", error);
  }
};

// --- NODE MANAGEMENT FUNCTIONS ---

const submitNode = async () => {
  try {
    if (isEditingNode.value) {
      // If editing, update the existing node
      await api.updateNode(form.value.id, form.value);
    } else {
      // If creating, add a new node to this generator
      await api.createNode(id, form.value);
    }
    
    // Reset form and refresh table
    form.value = { node_name: '', data_type_enum: 'String', generation_mode: 'Fixed' };
    isEditingNode.value = false;
    await loadData();
  } catch (error) {
    console.error("Failed to save node:", error);
    alert("Error saving node. Check console for details.");
  }
};

const editNode = (node) => {
  isEditingNode.value = true;
  // Clone the node data into the form so we don't directly mutate the table state
  form.value = { ...node }; 
};

const cancelEdit = () => {
  isEditingNode.value = false;
  form.value = { node_name: '', data_type_enum: 'String', generation_mode: 'Fixed' };
};

const removeNode = async (nodeId) => {
  if (!confirm("Are you sure you want to delete this node?")) return;
  
  try {
    await api.deleteNode(nodeId);
    await loadData(); // Refresh the table
  } catch (error) {
    console.error("Failed to delete node:", error);
  }
};

// --- SETTINGS MANAGEMENT ---

const updateSettings = async () => {
  try {
    await api.updateGenerator(id, {
      is_api_enabled: generator.value.is_api_enabled,
      is_message_broker_enabled: generator.value.is_message_broker_enabled
    });
  } catch (error) {
    console.error("Failed to update generator settings:", error);
  }
};

onMounted(() => { loadData(); startPolling(); loadApis(); loadMqtts();});
onUnmounted(() => clearInterval(pollingTimer));
</script>

