<template>
  <div class="auth-wrap">
    <div class="apple-card auth-card">
      <h1 class="auth-title">Create your account</h1>
      <p class="auth-sub">Your generators and configs stay private to you</p>

      <form @submit.prevent="submit" class="auth-form">
        <div class="form-group">
          <label>Username</label>
          <input v-model="username" type="text" class="apple-input" autocomplete="username" required />
        </div>
        <div class="form-group">
          <label>Password</label>
          <input v-model="password" type="password" class="apple-input" autocomplete="new-password" required />
        </div>
        <div class="form-group">
          <label>Confirm Password</label>
          <input v-model="confirm" type="password" class="apple-input" autocomplete="new-password" required />
        </div>

        <p v-if="error" class="auth-error">{{ error }}</p>

        <button type="submit" class="apple-btn-primary auth-submit" :disabled="loading">
          {{ loading ? 'Creating…' : 'Create Account' }}
        </button>
      </form>

      <p class="auth-switch">
        Already have an account?
        <router-link to="/login">Sign in</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import api, { auth } from '../services/api';

const router = useRouter();

const username = ref('');
const password = ref('');
const confirm = ref('');
const error = ref('');
const loading = ref(false);

const submit = async () => {
  error.value = '';
  if (password.value !== confirm.value) {
    error.value = 'Passwords do not match.';
    return;
  }
  if (password.value.length < 4) {
    error.value = 'Password must be at least 4 characters.';
    return;
  }
  loading.value = true;
  try {
    const res = await api.signup(username.value.trim(), password.value);
    auth.set(res.data.access_token, res.data.username);
    router.push('/dashboard');
  } catch (e) {
    error.value = e.response?.data?.detail || 'Sign up failed. Please try again.';
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
.auth-error { color: var(--danger); font-size: 13px; margin: 0 0 14px; }
.auth-switch { margin-top: 22px; font-size: 14px; color: var(--text-secondary); text-align: center; }
.auth-switch a { color: var(--link); font-weight: 500; }
</style>
