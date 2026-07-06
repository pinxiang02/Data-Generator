<template>
  <div class="auth-wrap">
    <div class="apple-card auth-card">
      <h1 class="auth-title">Welcome back</h1>
      <p class="auth-sub">Sign in to your DataGen account</p>

      <form @submit.prevent="submit" class="auth-form">
        <div class="form-group">
          <label>Username</label>
          <input v-model="username" type="text" class="apple-input" autocomplete="username" required />
        </div>
        <div class="form-group">
          <label>Password</label>
          <input v-model="password" type="password" class="apple-input" autocomplete="current-password" required />
        </div>

        <p v-if="error" class="auth-error">{{ error }}</p>

        <button type="submit" class="apple-btn-primary auth-submit" :disabled="loading">
          {{ loading ? 'Signing in…' : 'Sign In' }}
        </button>
      </form>

      <p class="auth-switch">
        Don't have an account?
        <router-link to="/signup">Create one</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api, { auth } from '../services/api';

const route = useRoute();
const router = useRouter();

const username = ref('');
const password = ref('');
const error = ref('');
const loading = ref(false);

const submit = async () => {
  error.value = '';
  loading.value = true;
  try {
    const res = await api.login(username.value.trim(), password.value);
    auth.set(res.data.access_token, res.data.username);
    router.push(route.query.redirect || '/dashboard');
  } catch (e) {
    error.value = e.response?.data?.detail || 'Login failed. Please try again.';
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.auth-wrap {
  min-height: calc(100vh - 48px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.auth-card {
  width: 100%;
  max-width: 380px;
  padding: 36px 32px;
}
.auth-title { font-size: 26px; font-weight: 600; margin-bottom: 6px; color: var(--text); }
.auth-sub { font-size: 15px; color: var(--text-secondary); margin-bottom: 26px; }
.auth-form .form-group { margin-bottom: 18px; }
.auth-submit { width: 100%; margin-top: 6px; }
.auth-submit:disabled { opacity: 0.6; cursor: default; }
.auth-error {
  color: var(--danger);
  font-size: 13px;
  margin: 0 0 14px;
}
.auth-switch { margin-top: 22px; font-size: 14px; color: var(--text-secondary); text-align: center; }
.auth-switch a { color: var(--link); font-weight: 500; }
</style>
