<template>
  <div id="app">
    <nav class="apple-nav">
      <div class="nav-container">
        <router-link to="/">DataGen</router-link>
        <router-link to="/generators">Generators</router-link>
        <router-link to="/api-config">API Config</router-link>
        <router-link to="/mqtt-config">MQTT Config</router-link>
      </div>
    </nav>
    <main>
      <router-view></router-view>
    </main>
  </div>
</template>

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
  justify-content: center;
  align-items: center;
}
.nav-container {
  display: flex;
  gap: 40px;
}
.nav-container a {
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
  letter-spacing: -0.12px;
}
.nav-container a:hover {
  color: white;
}
</style>