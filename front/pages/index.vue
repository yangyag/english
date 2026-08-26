<script setup lang="ts">
import { ApiError } from '~/composables/useEnglishApi'
import type { TodayOut, WordOut, WordResultIn } from '~/types/api'

const { getToday, submitReview, submitNew } = useEnglishApi()

const today = ref<TodayOut | null>(null)
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const index = ref(0)
const flipped = ref(false)
const results = ref<WordResultIn[]>([])

const deck = computed<WordOut[]>(() => {
  if (!today.value) return []
  if (today.value.phase === 'review') return today.value.review
  if (today.value.phase === 'new') return today.value.new
  return []
})

const current = computed(() => deck.value[index.value] ?? null)
const answered = computed(() => results.value.length)
const knownCount = computed(() => results.value.filter((item) => item.known).length)
const unknownCount = computed(() => results.value.filter((item) => !item.known).length)
const readyToSubmit = computed(
  () => deck.value.length > 0 && results.value.length === deck.value.length,
)
const phaseLabel = computed(() => {
  if (!today.value) return ''
  if (today.value.phase === 'review') return '복습'
  if (today.value.phase === 'new') return '신규'
  return '완료'
})

function resetDeck() {
  index.value = 0
  flipped.value = false
  results.value = []
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    today.value = await getToday()
    resetDeck()
  } catch (caught) {
    error.value = caught instanceof ApiError ? caught.detail : '오늘 학습을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

function flip() {
  if (readyToSubmit.value) return
  flipped.value = !flipped.value
}

function mark(known: boolean) {
  const word = current.value
  if (!word || !flipped.value || readyToSubmit.value) return
  results.value = [
    ...results.value.filter((item) => item.rank !== word.rank),
    { rank: word.rank, known },
  ]
  if (index.value < deck.value.length - 1) {
    index.value += 1
    flipped.value = false
  }
}

function undo() {
  if (results.value.length === 0) return
  results.value = results.value.slice(0, -1)
  index.value = Math.max(0, results.value.length)
  flipped.value = false
}

async function submit() {
  if (!today.value || !readyToSubmit.value) return
  submitting.value = true
  error.value = ''
  try {
    if (today.value.phase === 'review') {
      await submitReview(results.value)
    } else {
      await submitNew(results.value)
    }
    today.value = await getToday()
    resetDeck()
  } catch (caught) {
    if (caught instanceof ApiError && caught.status === 409) {
      await load()
      return
    }
    error.value = caught instanceof ApiError ? caught.detail : '제출에 실패했습니다.'
  } finally {
    submitting.value = false
  }
}

function onKey(event: KeyboardEvent) {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return
  if (event.key === ' ' || event.key === 'Enter') {
    event.preventDefault()
    flip()
  } else if (event.key === '1') {
    mark(true)
  } else if (event.key === '2') {
    mark(false)
  }
}

onMounted(load)
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <section class="today">
    <header class="head">
      <p class="kicker">{{ today?.date ?? '' }}</p>
      <h1>{{ phaseLabel || '오늘 학습' }}</h1>
      <p v-if="deck.length" class="meta">{{ answered }} / {{ deck.length }}</p>
    </header>

    <p v-if="error" class="banner error">{{ error }}</p>
    <p v-else-if="loading" class="banner">불러오는 중…</p>

    <template v-else-if="today?.phase === 'done'">
      <div class="done">
        <p class="done-title">오늘 학습을 마쳤습니다.</p>
        <p class="done-copy">내일은 마지막에 배운 10개를 복습한 뒤에 신규가 열립니다.</p>
        <NuxtLink class="link" to="/progress">진도 보기</NuxtLink>
      </div>
    </template>

    <template v-else-if="current">
      <ol class="dots" aria-label="진행">
        <li
          v-for="(word, i) in deck"
          :key="word.rank"
          :class="{
            'is-current': i === index,
            'is-known': results.find((item) => item.rank === word.rank)?.known === true,
            'is-unknown': results.find((item) => item.rank === word.rank)?.known === false,
          }"
        />
      </ol>

      <WordCard :key="current.rank" :word="current" :flipped="flipped" @flip="flip" />

      <div class="actions">
        <template v-if="readyToSubmit">
          <p class="summary">알아요 {{ knownCount }} · 몰라요 {{ unknownCount }}</p>
          <div class="row">
            <button type="button" class="ghost" :disabled="submitting" @click="undo">이전</button>
            <button type="button" class="primary" :disabled="submitting" @click="submit">
              {{ submitting ? '제출 중…' : '제출하기' }}
            </button>
          </div>
        </template>
        <template v-else-if="flipped">
          <div class="row">
            <button type="button" class="ghost" :disabled="answered === 0" @click="undo">이전</button>
            <button type="button" class="unknown" @click="mark(false)">몰라요</button>
            <button type="button" class="known" @click="mark(true)">알아요</button>
          </div>
        </template>
        <p v-else class="hint">카드를 뒤집은 다음 알아요 / 몰라요를 고릅니다.</p>
      </div>
    </template>
  </section>
</template>

<style scoped>
.today {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
  min-width: 0;
  width: 100%;
}
.head h1 { margin: 4px 0 0; font-size: 1.6rem; }
.kicker, .meta { margin: 0; color: #6b6258; font-size: 0.92rem; }
.banner { margin: 0; color: #5b5348; }
.banner.error { color: #9b2c22; }
.done { padding: 24px 8px 8px; text-align: center; }
.done-title { margin: 0 0 8px; font-size: 1.25rem; font-weight: 700; }
.done-copy { margin: 0 0 20px; color: #5b5348; line-height: 1.5; }
.link { color: #1e2a24; font-weight: 700; }
.dots {
  display: flex;
  gap: 6px;
  list-style: none;
  margin: 0;
  padding: 0;
  justify-content: center;
  min-width: 0;
}
.dots li {
  display: block;
  box-sizing: border-box;
  flex: 0 0 10px;
  width: 10px;
  height: 10px;
  min-width: 10px;
  max-width: 10px;
  border-radius: 50%;
  background: #d9d0c2;
}
.dots li.is-current { outline: 2px solid #1e2a24; outline-offset: 2px; }
.dots li.is-known { background: #2c6e49; }
.dots li.is-unknown { background: #b23a2f; }
.actions { min-height: 88px; }
.hint, .summary { margin: 12px 0; text-align: center; color: #5b5348; }
.row {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
  min-width: 0;
}
button {
  border: 0;
  border-radius: 999px;
  padding: 12px 18px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}
button:disabled { opacity: 0.5; cursor: not-allowed; }
.ghost { background: #ece6da; color: #1c1914; }
button.known { background: #2c6e49; color: #fff; min-width: 112px; }
button.unknown { background: #b23a2f; color: #fff; min-width: 112px; }
.primary { background: #1e2a24; color: #f4efe4; min-width: 140px; }
</style>
