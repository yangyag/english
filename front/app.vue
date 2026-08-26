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
body {
  margin: 0;
  font-family: 'Pretendard', -apple-system, 'Segoe UI', Roboto, sans-serif;
  background: #f6f7fb;
  color: #1f2430;
}
.app { max-width: 640px; margin: 0 auto; padding: 16px; }
.nav {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  margin-bottom: 16px;
  border-bottom: 1px solid #e3e6ee;
}
.nav a { text-decoration: none; color: #55607a; font-weight: 600; }
.nav a.router-link-active { color: #2f6fed; }
.main { background: #fff; border-radius: 12px; padding: 20px; }
</style>
