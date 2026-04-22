import { createRouter, createWebHistory } from 'vue-router';
import HomeView from '../views/HomeView.vue';

const routes = [
  {
    path: '/',
    name: 'Home',
    component: HomeView,
    meta: { title: 'Home - DataGen' }
  },
  {
    path: '/generators',
    name: 'Generators',
    component: () => import('../views/GeneratorsView.vue'),
    meta: { title: 'Generators - DataGen' }
  },
  {
    path: '/generators/:id/nodes',
    name: 'GeneratorNodes',
    component: () => import('../views/GeneratorNodesView.vue'),
    props: true,
    meta: { title: 'Configure Nodes - DataGen' }
  },
  {
    path: '/api-config',
    name: 'ApiConfig',
    component: () => import('../views/ApiConfigView.vue'),
    meta: { title: 'API Configuration - DataGen' }
  },
  {
    path: '/mqtt-config',
    name: 'MqttConfig',
    component: () => import('../views/MqttConfigView.vue'),
    meta: { title: 'MQTT Configuration - DataGen' }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// Automatically update the document title on route change
router.beforeEach((to, from, next) => {
  document.title = to.meta.title || 'DataGen';
  next();
});

export default router;