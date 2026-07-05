<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">Database Destinations</h1>
      <button @click="openCreateModal" class="apple-btn-primary">Add Database</button>
    </div>

    <div class="apple-card" style="padding: 0; overflow: hidden;">
      <table class="apple-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Type</th>
            <th>Table</th>
            <th style="text-align: right;">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="databases.length === 0">
            <td colspan="5" class="empty-state">No database destinations configured.</td>
          </tr>
          <tr v-for="d in databases" :key="d.DBid">
            <td style="color: var(--text-secondary);">#{{ d.DBid }}</td>
            <td style="font-weight: 500;">{{ d.DBName }}</td>
            <td><span class="badge">{{ d.DBType }}</span></td>
            <td class="font-mono">{{ d.TableName }}</td>
            <td>
              <div class="table-actions" style="justify-content: flex-end;">
                <button @click="autoGenerate(d)" class="action-btn edit-color" title="Create a generator from this table's schema">Generate</button>
                <button @click="editDatabase(d)" class="action-btn edit-color">Edit</button>
                <button @click="deleteDatabase(d.DBid)" class="action-btn delete-color">Delete</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p class="hint-note">
      The application inserts into an <strong>existing</strong> table — it never creates or alters tables.
      Your generator's node names &amp; types must match the table columns.
      Use <strong>Generate</strong> to auto-build a matching generator from a table's schema.
    </p>

    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content slide-down">
        <div class="modal-header">
          <h2 class="modal-title">{{ isEditing ? 'Edit Database' : 'New Database Destination' }}</h2>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Connection Name</label>
            <input v-model="form.DBName" type="text" class="apple-input" placeholder="e.g., Factory Warehouse DB">
          </div>

          <div class="form-group">
            <label>Database Type</label>
            <select v-model="form.DBType" class="apple-input">
              <option value="PostgreSQL">PostgreSQL</option>
              <option value="MySQL">MySQL</option>
              <option value="Oracle">Oracle</option>
              <option value="MongoDB">MongoDB</option>
            </select>
          </div>

          <div class="form-group">
            <label>Connection String</label>
            <input v-model="form.ConnectionString" type="text" class="apple-input" :placeholder="connHint">
          </div>

          <div class="form-group">
            <label>{{ tableLabel }}</label>
            <input v-model="form.TableName" type="text" class="apple-input" :placeholder="tablePlaceholder">
          </div>

          <div v-if="testResult" class="test-result-row">
            <span class="test-result" :class="testResult.ok ? 'ok' : 'bad'">
              {{ testResult.message }}
            </span>
          </div>

          <div v-if="testResult && testResult.ok && testResult.columns" class="cols-preview">
            <div class="cols-title">Table columns</div>
            <div class="cols-list">
              <span v-for="(meta, col) in testResult.columns" :key="col" class="col-chip">
                {{ col }} <em>{{ meta.type }}</em>
              </span>
            </div>
          </div>
        </div>
        <div class="modal-footer db-footer">
          <button type="button" @click="testConnection" class="apple-btn apple-btn-secondary" :disabled="testing">
            {{ testing ? 'Testing…' : 'Test Connection' }}
          </button>
          <div class="footer-actions">
            <button @click="closeModal" class="apple-btn apple-btn-secondary">Cancel</button>
            <button @click="submit" class="apple-btn-primary">{{ isEditing ? 'Save Changes' : 'Save Database' }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import api from '../services/api';

const router = useRouter();

const CONN_HINTS = {
  PostgreSQL: 'postgresql://user:password@host:5432/dbname',
  MySQL: 'mysql://user:password@host:3306/dbname',
  Oracle: 'oracle://user:password@host:1521/?service_name=FREEPDB1',
  MongoDB: 'mongodb://user:password@host:27017/dbname?authSource=admin',
};
const connHint = computed(() => CONN_HINTS[form.value.DBType] || CONN_HINTS.PostgreSQL);
const isMongo = computed(() => form.value.DBType === 'MongoDB');
const tableLabel = computed(() => (isMongo.value ? 'Target Collection' : 'Target Table'));
const tablePlaceholder = computed(() => (isMongo.value ? 'events' : 'sensor_readings'));
const databases = ref([]);
const showModal = ref(false);
const isEditing = ref(false);
const editId = ref(null);
const testing = ref(false);
const testResult = ref(null);

const blank = () => ({ DBName: '', DBType: 'PostgreSQL', ConnectionString: '', TableName: '' });
const form = ref(blank());

const loadDatabases = async () => {
  try { databases.value = (await api.getDatabases()).data; }
  catch (error) { console.error('Failed to load databases:', error); }
};

const openCreateModal = () => {
  isEditing.value = false;
  editId.value = null;
  testResult.value = null;
  form.value = blank();
  showModal.value = true;
};

const editDatabase = (d) => {
  isEditing.value = true;
  editId.value = d.DBid;
  testResult.value = null;
  form.value = { DBName: d.DBName, DBType: d.DBType, ConnectionString: d.ConnectionString, TableName: d.TableName };
  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
  isEditing.value = false;
  editId.value = null;
  testResult.value = null;
  form.value = blank();
};

const testConnection = async () => {
  testing.value = true;
  testResult.value = null;
  try {
    const res = await api.testDatabase({
      DBType: form.value.DBType,
      ConnectionString: form.value.ConnectionString,
      TableName: form.value.TableName || null,
    });
    testResult.value = res.data;
  } catch (e) {
    testResult.value = { ok: false, message: e.response?.data?.detail || 'Test failed.' };
  } finally {
    testing.value = false;
  }
};

const submit = async () => {
  if (!form.value.DBName || !form.value.ConnectionString || !form.value.TableName) {
    alert('Name, connection string and table are required.');
    return;
  }
  try {
    if (isEditing.value) await api.updateDatabase(editId.value, form.value);
    else await api.createDatabase(form.value);
    closeModal();
    loadDatabases();
  } catch (e) {
    alert(e.response?.data?.detail || 'Failed to save database config.');
  }
};

const deleteDatabase = async (id) => {
  if (!confirm('Delete this database destination?')) return;
  try { await api.deleteDatabase(id); loadDatabases(); }
  catch (e) { console.error('Failed to delete:', e); }
};

const autoGenerate = async (d) => {
  if (!confirm(`Auto-create a generator from the schema of table "${d.TableName}"?`)) return;
  try {
    const res = await api.generateGeneratorFromDatabase(d.DBid);
    const { generator, nodes_created, skipped_auto_columns } = res.data;
    const skipped = skipped_auto_columns.length ? `\nSkipped auto columns: ${skipped_auto_columns.join(', ')}` : '';
    if (confirm(`Created "${generator.name}" with ${nodes_created} nodes.${skipped}\n\nOpen it now?`)) {
      router.push(`/generators/${generator.id}/nodes`);
    }
  } catch (e) {
    alert(e.response?.data?.detail || 'Failed to generate generator from schema.');
  }
};

onMounted(loadDatabases);
</script>

<style scoped>
.hint-note {
  margin-top: 16px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}
.field-warn {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: #ff9f0a;
}
/* All three footer buttons on one line: Test on the left, Cancel/Save on the right */
.db-footer {
  justify-content: space-between;
}
.footer-actions {
  display: flex;
  gap: 12px;
}
.test-result-row { margin-top: 10px; }
.test-result { font-size: 13px; }
.test-result.ok { color: var(--success); }
.test-result.bad { color: var(--danger); }
.cols-preview {
  margin-top: 14px;
  background: var(--surface-2);
  border-radius: 10px;
  padding: 12px;
}
.cols-title { font-size: 12px; color: var(--text-secondary); margin-bottom: 8px; font-weight: 500; }
.cols-list { display: flex; flex-wrap: wrap; gap: 6px; }
.col-chip {
  font-size: 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 3px 8px;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.col-chip em { color: var(--text-secondary); font-style: normal; }
</style>
