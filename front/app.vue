<template>
  <div class="app">
    <header class="site-header">
      <NuxtLink class="brand" to="/"><span class="brand-icon">w.</span> 단어의 날들</NuxtLink>
      <nav aria-label="메인 메뉴"><NuxtLink to="/">학습 달력</NuxtLink><NuxtLink to="/progress">진도</NuxtLink></nav>
    </header>
    <main><NuxtPage /></main>
    <footer>조금씩, 나의 속도로.</footer>
  </div>
</template>
<style>
* { box-sizing: border-box; }
body { margin: 0; background: #f5f4ef; color: #263e35; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
button, a { -webkit-tap-highlight-color: transparent; }
button { font: inherit; cursor: pointer; }
button:disabled { cursor: default; opacity: .45; }
button:focus-visible, a:focus-visible { outline: 3px solid #c17a3f; outline-offset: 4px; }
a { color: inherit; }
.app { max-width: 1120px; padding: 0 32px; margin: auto; }
.site-header { display: flex; align-items: center; justify-content: space-between; padding: 28px 0; border-bottom: 1px solid #dedfd5; gap: 16px; }
.brand { display: flex; gap: 10px; align-items: center; font-weight: 750; text-decoration: none; }
.brand-icon { background: #284c3e; color: #fff; padding: 6px 10px; border-radius: 10px; font-family: Georgia, serif; font-size: 24px; }
nav { display: flex; gap: 24px; font-size: 14px; } nav a { text-decoration: none; color: #727c74; } nav a.router-link-exact-active { color: #284c3e; font-weight: 700; }
main { padding: 42px 0; min-height: 75vh; } footer { border-top: 1px solid #dedfd5; padding: 24px 0; font-size: 13px; color: #7b8178; }
h1 { font-size: clamp(27px, 4vw, 36px); letter-spacing: -.04em; margin: 6px 0 12px; }
h2 { font-size: 20px; letter-spacing: -.025em; } p { line-height: 1.65; }
.muted { color: #758075; } .eyebrow { font-size: 12px; letter-spacing: .14em; text-transform: uppercase; color: #718174; margin: 0; }
.panel { background: #fffefa; border: 1px solid #e1e3d9; border-radius: 20px; padding: 26px; }
.primary, .secondary { border: 0; border-radius: 12px; padding: 14px 20px; font-weight: 650; }
.primary { color: #fff; background: #284c3e; } .secondary { background: #eaf0e5; color: #284c3e; }
.error { color: #a23f30; background: #fff0e9; padding: 12px; border-radius: 10px; }
@media (max-width: 640px) { .app { padding: 0 16px; } .site-header { padding: 18px 0; } nav { gap: 16px; } main { padding: 28px 0; } .panel { padding: 18px; } .brand { font-size: 14px; } }
</style>
