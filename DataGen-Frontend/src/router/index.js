import { createRouter, createWebHistory } from 'vue-router';
import HomeView from '../views/HomeView.vue';
import { auth } from '../services/api';

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { title: 'Sign In - DataGen', public: true },
  },
  {
    path: '/signup',
    name: 'Signup',
    component: () => import('../views/SignupView.vue'),
    meta: { title: 'Sign Up - DataGen', public: true },
  },
  {
    path: '/',
    name: 'Home',
    component: HomeView,
    meta: { title: 'Home - DataGen' },
  },
  {
    path: '/generators',
    name: 'Generators',
    component: () => import('../views/GeneratorsView.vue'),
    meta: { title: 'Generators - DataGen' },
  },
  {
    path: '/generators/:id/nodes',
    name: 'GeneratorNodes',
    component: () => import('../views/GeneratorNodesView.vue'),
    props: true,
    meta: { title: 'Configure Nodes - DataGen' },
  },
  {
    path: '/api-config',
    name: 'ApiConfig',
    component: () => import('../views/ApiConfigView.vue'),
    meta: { title: 'API Configuration - DataGen' },
  },
  {
    path: '/mqtt-config',
    name: 'MqttConfig',
    component: () => import('../views/MqttConfigView.vue'),
    meta: { title: 'MQTT Configuration - DataGen' },
  },
  {
    path: '/database-config',
    name: 'DatabaseConfig',
    component: () => import('../views/DatabaseConfigView.vue'),
    meta: { title: 'Database Configuration - DataGen' },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  document.title = to.meta.title || 'DataGen';

  // Protect everything except pages explicitly marked public.
  if (!to.meta.public && !auth.isAuthenticated) {
    return next({ name: 'Login', query: { redirect: to.fullPath } });
  }
  // Logged-in users shouldn't sit on the login/signup pages.
  if (to.meta.public && auth.isAuthenticated) {
    return next({ name: 'Generators' });
  }
  next();
});

export default router;
