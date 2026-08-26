<script setup lang="ts">
import { ApiError } from '~/composables/useEnglishApi'
import type { ProgressOut } from '~/types/api'

const { getProgress } = useEnglishApi()
const progress = ref<ProgressOut | null>(null)
const loading = ref(true)
const error = ref('')

const percent = computed(() => {
  if (!progress.value || progress.value.total_words === 0) return 0
  return Math.min(100, Math.round((progress.value.learned_count / progress.value.total_words) * 100))
})

function formatDate(iso: string | null): string {
  if (!iso) return '아직 없음'
  const [year, month, day] = iso.split('-')
  return `${year}년 ${Number(month)}월 ${Number(day)}일`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    progress.value = await getProgress()
  } catch (caught) {
    error.value = caught instanceof ApiError ? caught.detail : '진도를 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="progress">
    <header>
      <h1>진도</h1>
    </header>

    <p v-if="error" class="banner error">{{ error }}</p>
    <p v-else-if="loading" class="banner">불러오는 중…</p>

    <template v-else-if="progress">
      <div class="hero">
        <p class="count">
          <strong>{{ progress.learned_count.toLocaleString() }}</strong>
          <span> / {{ progress.total_words.toLocaleString() }}</span>
        </p>
        <div class="bar" role="progressbar" :aria-valuenow="percent" aria-valuemin="0" aria-valuemax="100">
          <span :style="{ width: percent + '%' }" />
        </div>
        <p class="percent">{{ percent }}%</p>
      </div>

      <ul class="stats">
        <li>
          <span>다음 순위</span>
          <strong>{{ progress.next_rank.toLocaleString() }}</strong>
        </li>
        <li>
          <span>연속 학습</span>
          <strong>{{ progress.streak_days }}일</strong>
        </li>
        <li>
          <span>마지막 학습</span>
          <strong>{{ formatDate(progress.last_study_date) }}</strong>
        </li>
      </ul>
    </template>
  </section>
</template>

<style scoped>
.progress h1 { margin: 0 0 16px; font-size: 1.6rem; }
.banner { color: #5b5348; }
.banner.error { color: #9b2c22; }
.hero { text-align: center; padding: 8px 0 20px; }
.count { margin: 0 0 12px; font-size: 1.1rem; color: #5b5348; }
.count strong { font-size: 2.2rem; color: #1c1914; }
.bar {
  height: 10px;
  background: #e4dccb;
  border-radius: 999px;
  overflow: hidden;
}
.bar span {
  display: block;
  height: 100%;
  background: #1e2a24;
  border-radius: inherit;
}
.percent { margin: 8px 0 0; color: #6b6258; }
.stats {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}
.stats li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 0;
  border-top: 1px solid #e4dccb;
  color: #5b5348;
}
.stats strong { color: #1c1914; }
</style>
