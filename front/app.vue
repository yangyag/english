<template>
  <div class="app">
    <nav class="nav">
      <NuxtLink to="/">오늘 학습</NuxtLink>
      <NuxtLink to="/progress">진도</NuxtLink>
    </nav>
    <main class="main">
      <NuxtPage />
    </main>
  </div>
</template>

<style>
* { box-sizing: border-box; }
html, body {
  min-height: 100%;
  max-width: 100%;
  overflow-x: hidden;
}
body {
  margin: 0;
  font-family: 'Pretendard', -apple-system, 'Segoe UI', Roboto, sans-serif;
  background: #f3efe4;
  color: #1c1914;
}
.app {
  width: 100%;
  max-width: 640px;
  margin: 0 auto;
  padding: 16px 16px 40px;
  overflow-x: hidden;
}
.nav {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  margin-bottom: 16px;
  border-bottom: 1px solid #e4dccb;
}
.nav a { text-decoration: none; color: #6b6258; font-weight: 700; }
.nav a.router-link-active { color: #1e2a24; }
.main {
  background: #fffaf1;
  border: 1px solid #e4dccb;
  border-radius: 16px;
  padding: 20px;
  overflow: hidden;
  min-width: 0;
}
</style>
