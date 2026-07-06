<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">Dashboard</h1>
      <router-link to="/generators" class="apple-btn-primary" style="text-decoration:none;">Manage Generators</router-link>
    </div>

    <!-- Summary stat cards -->
    <div class="stat-grid">
      <div class="apple-card stat-card">
        <div class="stat-label">Generators</div>
        <div class="stat-value">{{ generators.length }}</div>
      </div>
      <div class="apple-card stat-card">
        <div class="stat-label">Running</div>
        <div class="stat-value">
          <span class="run-dot" :class="{ on: runningCount > 0 }"></span>{{ runningCount }}
        </div>
      </div>
      <div class="apple-card stat-card">
        <div class="stat-label">Messages Sent</div>
        <div class="stat-value">{{ totalMessages.toLocaleString() }}</div>
      </div>
      <div class="apple-card stat-card">
        <div class="stat-label">Throughput</div>
        <div class="stat-value">{{ aggregateRate.toFixed(1) }} <span class="unit">msg/s</span></div>
      </div>
    </div>

    <!-- Per-generator table -->
    <div class="apple-card" style="padding: 0; overflow: hidden; margin-top: 24px;">
      <table class="apple-table">
        <thead>
          <tr>
            <th style="padding-left: 20px;">Generator</th>
            <th>Status</th>
            <th style="text-align:right;">Messages</th>
            <th style="text-align:right;">Rate</th>
            <th style="text-align:center;">Activity</th>
            <th style="text-align:right; padding-right: 20px;">Controls</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="generators.length === 0">
            <td colspan="6" class="empty-state">No generators yet. Create one to see it here.</td>
          </tr>
          <tr v-for="gen in generators" :key="gen.id">
            <td style="padding-left: 20px;">
              <router-link :to="`/generators/${gen.id}/nodes`" class="gen-name">{{ gen.name }}</router-link>
              <div class="gen-desc">{{ gen.description || '—' }}</div>
            </td>
            <td>
              <span class="status-badge" :class="isRunning(gen.id) ? 'is-running' : 'is-idle'">
                <span class="status-led"></span>{{ isRunning(gen.id) ? 'Running' : 'Idle' }}
              </span>
            </td>
            <td style="text-align:right; font-variant-numeric: tabular-nums;">{{ msgCount(gen.id).toLocaleString() }}</td>
            <td style="text-align:right; font-variant-numeric: tabular-nums;">{{ rate(gen.id).toFixed(1) }}<span class="unit"> /s</span></td>
            <td style="text-align:center;">
              <svg class="spark" viewBox="0 0 120 28" preserveAspectRatio="none" width="120" height="28">
                <polyline v-if="sparkPoints(gen.id)" :points="sparkPoints(gen.id)"
                          fill="none" :stroke="isRunning(gen.id) ? 'var(--success)' : 'var(--text-secondary)'"
                          stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" />
              </svg>
            </td>
            <td style="text-align:right; padding-right: 20px;">
              <div class="table-actions" style="justify-content:flex-end;">
                <button v-if="!isRunning(gen.id)" @click="start(gen.id)" class="apple-btn-success small-btn">Start</button>
                <button v-else @click="stop(gen.id)" class="apple-btn-danger small-btn">Stop</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import api from '../services/api';

const generators = ref([]);
const status = ref({});          // { gid: { running, count } }
const rates = ref({});           // { gid: msgs/sec }
const history = ref({});         // { gid: [rate, ...] }  (sparkline)
const lastSample = {};           // { gid: { count, t } }  (throughput deltas)
let timer = null;

const SPARK_LEN = 24;

const isRunning = (id) => !!status.value[id]?.running;
const msgCount = (id) => status.value[id]?.count || 0;
const rate = (id) => rates.value[id] || 0;

const runningCount = computed(() => Object.values(status.value).filter(s => s.running).length);
const totalMessages = computed(() => Object.values(status.value).reduce((a, s) => a + (s.count || 0), 0));
const aggregateRate = computed(() => Object.values(rates.value).reduce((a, r) => a + r, 0));

// Build an SVG polyline for a generator's recent rate history.
const sparkPoints = (id) => {
  const h = history.value[id];
  if (!h || h.length < 2) return '';
  const max = Math.max(...h, 1);
  const n = h.length;
  return h.map((v, i) => {
    const x = (i / (n - 1)) * 120;
    const y = 28 - (v / max) * 26 - 1;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
};

const loadGenerators = async () => {
  try { generators.value = (await api.getGenerators()).data; }
  catch (e) { /* handled by interceptor */ }
};

const poll = async () => {
  let data;
  try { data = (await api.getGeneratorsStatus()).data; }
  catch (e) { return; }
  const now = Date.now();

  // Compute per-generator throughput from the count delta since last sample.
  for (const [gid, s] of Object.entries(data)) {
    const prev = lastSample[gid];
    let r = 0;
    if (prev) {
      const dt = (now - prev.t) / 1000;
      if (dt > 0) r = Math.max(0, (s.count - prev.count) / dt);
    }
    lastSample[gid] = { count: s.count, t: now };
    rates.value[gid] = r;

    const hist = (history.value[gid] || []).concat(r);
    if (hist.length > SPARK_LEN) hist.shift();
    history.value[gid] = hist;
  }
  status.value = data;
};

const start = async (id) => {
  try { await api.startGenerator(id); await poll(); }
  catch (e) { alert(e.response?.data?.detail || 'Error starting'); }
};
const stop = async (id) => {
  try { await api.stopGenerator(id); await poll(); }
  catch (e) { alert(e.response?.data?.detail || 'Error stopping'); }
};

onMounted(async () => {
  await loadGenerators();
  await poll();
  timer = setInterval(poll, 2000);   // live throughput + status
});
onUnmounted(() => clearInterval(timer));
</script>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
@media (max-width: 720px) { .stat-grid { grid-template-columns: repeat(2, 1fr); } }
.stat-card { padding: 20px 22px; }
.stat-label { font-size: 13px; color: var(--text-secondary); font-weight: 500; margin-bottom: 8px; }
.stat-value { font-size: 30px; font-weight: 600; letter-spacing: -0.5px; display: flex; align-items: center; gap: 8px; }
.stat-value .unit { font-size: 14px; color: var(--text-secondary); font-weight: 500; }
.run-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--text-secondary); }
.run-dot.on { background: var(--success); box-shadow: 0 0 8px var(--success); }

.gen-name { font-weight: 500; color: var(--text); }
.gen-name:hover { color: var(--link); }
.gen-desc { font-size: 12px; color: var(--text-secondary); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 260px; }
.unit { font-size: 12px; color: var(--text-secondary); }

.status-badge { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 500; padding: 3px 10px; border-radius: 980px; }
.status-led { width: 7px; height: 7px; border-radius: 50%; }
.status-badge.is-running { background: rgba(52,199,89,0.15); color: #30d158; }
.status-badge.is-running .status-led { background: #34c759; box-shadow: 0 0 6px #34c759; }
.status-badge.is-idle { background: var(--surface-2); color: var(--text-secondary); }
.status-badge.is-idle .status-led { background: var(--text-secondary); }

.spark { display: inline-block; vertical-align: middle; }
.small-btn { padding: 6px 14px; font-size: 13px; }
</style>
