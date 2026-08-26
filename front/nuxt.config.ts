// Nuxt 설정. SSR 없이 정적 생성으로만 배포한다 (PLAN.md 참고).
export default defineNuxtConfig({
  ssr: false,
  compatibilityDate: '2026-08-26',
  devtools: { enabled: false },
  typescript: { strict: true },
  app: {
    head: {
      title: '오늘의 영어단어',
      htmlAttrs: { lang: 'ko' },
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      ],
    },
  },
  // 로컬 개발: /v1 을 로컬 FastAPI(8090)로 프록시.
  // 운영: nginx 가 /v1 을 프록시하므로 앱 코드는 상대 경로만 쓴다.
  nitro: {
    devProxy: {
      '/v1': { target: 'http://127.0.0.1:8090/v1', changeOrigin: true },
    },
  },
})
