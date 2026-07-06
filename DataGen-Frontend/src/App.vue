<template>
  <div id="app">
    <nav class="apple-nav">
      <div class="nav-left">
        <span class="brand">DataGen</span>
      </div>

      <div class="nav-container" v-if="isAuthed">
        <router-link to="/dashboard">Dashboard</router-link>
        <router-link to="/generators">Generators</router-link>
        <router-link to="/api-config">API Config</router-link>
        <router-link to="/mqtt-config">MQTT Config</router-link>
        <router-link to="/database-config">Database Config</router-link>
      </div>

      <div class="nav-right">
        <span v-if="isAuthed" class="nav-user">{{ username }}</span>
        <button v-if="isAuthed" class="nav-logout" @click="logout">Log out</button>
        <button
          class="theme-toggle"
          @click="toggleTheme"
          :aria-label="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
          :title="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
        >
          <svg v-if="theme === 'dark'" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
          </svg>
        </button>
      </div>
    </nav>
    <main>
      <router-view></router-view>
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { auth } from './services/api';

const route = useRoute();
const router = useRouter();

// Reading route.fullPath makes these recompute on every navigation
// (login/logout both navigate), keeping the nav in sync with auth state.
const isAuthed = computed(() => (route.fullPath, auth.isAuthenticated));
const username = computed(() => (route.fullPath, auth.username));

const logout = () => {
  auth.clear();
  router.push({ name: 'Login' });
};

// --- Theme ---
const STORAGE_KEY = 'datagen-theme';
const current = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
const theme = ref(current);

const toggleTheme = () => {
  theme.value = theme.value === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', theme.value);
  try {
    localStorage.setItem(STORAGE_KEY, theme.value);
  } catch (e) { /* localStorage may be unavailable */ }
};
</script>

<style scoped>
.apple-nav {
  position: sticky;
  top: 0;
  z-index: 1000;
  height: 48px;
  background-color: var(--nav-bg);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  transition: background-color 0.3s ease;
}
.nav-left, .nav-right {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
}
.nav-right { justify-content: flex-end; }
.brand {
  color: var(--nav-text-hover);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.2px;
}
.nav-container {
  display: flex;
  gap: 32px;
}
.nav-container a {
  color: var(--nav-text);
  font-size: 12px;
  letter-spacing: -0.12px;
}
.nav-container a:hover,
.nav-container a.router-link-active {
  color: var(--nav-text-hover);
}
.nav-user {
  color: var(--nav-text);
  font-size: 12px;
  font-weight: 500;
}
.nav-logout {
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.9);
  border: none;
  border-radius: 980px;
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease;
}
.nav-logout:hover { background: rgba(255, 255, 255, 0.22); }
.theme-toggle {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.9);
  transition: background 0.2s ease, transform 0.1s ease;
}
.theme-toggle:hover { background: rgba(255, 255, 255, 0.22); }
.theme-toggle:active { transform: scale(0.92); }
.theme-toggle svg { pointer-events: none; }
</style>
