<script setup lang="ts">
import type { CalendarOut, DayOut, ProgressOut, TodayOut, SubmitIn, WordOut } from '~/types/api'
import { ApiError } from '~/composables/useEnglishApi'
const api = useEnglishApi()
const today = ref<TodayOut | null>(null)
const progress = ref<ProgressOut | null>(null)
const calendar = ref<CalendarOut | null>(null)
const detail = ref<DayOut | null>(null)
const month = ref('')
const selected = ref('')
const error = ref('')
const notice = ref('')
const loading = ref(true)
const submitting = ref(false)
const flipped = ref(false)
type Draft = { kind: 'new' | 'review'; words: WordOut[]; body: SubmitIn }
const draft = ref<Draft | null>(null)
const storageKey = 'english-study-draft-v3'
const current = computed(() => draft.value?.words[0])
const pending = computed(() => !!draft.value?.body.results.length)
const savedToday = computed(() => today.value ? today.value.new_count + today.value.review_count : 0)
const monthTitle = computed(() => month.value ? `${month.value.slice(0, 4)}년 ${Number(month.value.slice(5))}월` : '')
const days = computed(() => {
  if (!month.value) return []
  const [y, m] = month.value.split('-').map(Number) as [number, number]
  const offset = new Date(y, m - 1, 1).getDay()
  const count = new Date(y, m, 0).getDate()
  return Array.from({ length: Math.ceil((offset + count) / 7) * 7 }, (_, i) => {
    const n = i - offset + 1
    if (n < 1 || n > count) return null
    const date = `${month.value}-${String(n).padStart(2, '0')}`
    return { n, date, record: calendar.value?.days.find(d => d.date === date) }
  })
})
let calendarRequest = 0
let detailRequest = 0
async function loadMonth() {
  const id = ++calendarRequest
  calendar.value = null
  try { const data = await api.getCalendar(month.value); if (id === calendarRequest) calendar.value = data }
  catch (e) { if (id === calendarRequest) error.value = (e as Error).message }
}
async function selectDay(day: string) {
  selected.value = day
  detail.value = null
  const id = ++detailRequest
  try { const data = await api.getDay(day); if (id === detailRequest) detail.value = data }
  catch (e) { if (id === detailRequest) error.value = (e as Error).message }
}
function moveMonth(delta: number) {
  const [y, m] = month.value.split('-').map(Number) as [number, number]
  const date = new Date(y, m - 1 + delta, 1)
  month.value = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
  void loadMonth()
  void selectDay(month.value === today.value?.date.slice(0, 7) ? today.value.date : `${month.value}-01`)
}
function persist() {
  try { if (draft.value) localStorage.setItem(storageKey, JSON.stringify(draft.value)); else localStorage.removeItem(storageKey) }
  catch { notice.value = '이 브라우저에서는 임시 저장을 사용할 수 없습니다. 저장이 확인될 때까지 화면을 유지해 주세요.' }
}
async function load() {
  loading.value = true; error.value = ''
  try {
    ;[today.value, progress.value] = await Promise.all([api.getToday(), api.getProgress()])
    month.value ||= today.value.date.slice(0, 7)
    selected.value ||= today.value.date
    await Promise.all([loadMonth(), selectDay(selected.value)])
  } catch (e) { error.value = (e as Error).message }
  finally { loading.value = false }
}
async function start(kind: 'new' | 'review') {
  error.value = ''; notice.value = ''
  try {
    today.value = await api.getToday()
    const words = today.value[kind].slice(0, 1)
    if (!words.length) { notice.value = '이 학습은 모두 완료했어요.'; return }
    draft.value = { kind, words, body: { request_id: crypto.randomUUID(), study_date: today.value.date,
      source_date: kind === 'review' ? today.value.review_source_date : null, results: [] } }
    flipped.value = false; persist()
  } catch (e) { error.value = (e as Error).message }
}
async function mark(known: boolean | null) {
  if (!draft.value || !current.value || !flipped.value || submitting.value || pending.value) return
  draft.value.body.results = [{ rank: current.value.rank, known }]
  persist()
  await submit()
}
async function leave() {
  if (submitting.value || pending.value) return
  draft.value = null; flipped.value = false; persist()
  month.value = ''; selected.value = ''
  await load()
}
async function submit() {
  if (!draft.value || !pending.value || submitting.value) return
  submitting.value = true; error.value = ''
  try {
    const kind = draft.value.kind
    today.value = await api.submit(kind, draft.value.body)
    const words = today.value[kind].slice(0, 1)
    draft.value = words.length ? { kind, words, body: { request_id: crypto.randomUUID(), study_date: today.value.date,
      source_date: kind === 'review' ? today.value.review_source_date : null, results: [] } } : null
    flipped.value = false
    notice.value = words.length
      ? `오늘 ${savedToday.value}개 학습을 저장했어요. 언제든 돌아가도 기록은 남아요.`
      : `학습을 모두 마쳤어요. 오늘 ${savedToday.value}개 학습을 저장했어요.`
    persist()
    if (!draft.value) { month.value = ''; selected.value = ''; await load() }
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) {
      draft.value = null; flipped.value = false; persist()
      notice.value = `${e.message} 저장된 기록을 확인한 뒤 이어서 시작해 주세요.`
      month.value = ''; selected.value = ''; await load()
    } else {
      error.value = '저장을 확인하지 못했어요. 다시 시도해 주세요. 같은 응답은 한 번만 기록됩니다.'
    }
  } finally { submitting.value = false }
}
onMounted(async () => {
  await load()
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || 'null')
    if (saved && ['new', 'review'].includes(saved.kind) && Array.isArray(saved.words) && saved.words.length > 0
      && saved.words.length === 1 && Array.isArray(saved.body?.results) && saved.body.results.length <= 1
      && saved.body.results.every((r: { rank: number; known: unknown }) => r.rank === saved.words[0].rank
        && (saved.kind === 'new' ? r.known === null : typeof r.known === 'boolean'))
      && typeof saved.body.request_id === 'string') {
      draft.value = saved; flipped.value = !!saved.body.results.length
      notice.value = saved.body.results.length ? '저장이 확인되지 않은 응답이 있어요. 저장 다시 시도를 눌러 주세요.' : '진행 중이던 학습을 불러왔어요.'
    } else if (localStorage.getItem('english-study-draft-v2')) {
      notice.value = '이전 방식의 미제출 학습이 있어요. 저장된 진도부터 다시 시작해 주세요.'
    }
  } catch { localStorage.removeItem(storageKey) }
})
</script>

<template>
  <div>
    <p v-if="error" class="error" role="alert">{{ error }} <button v-if="!pending" class="secondary" :disabled="loading || submitting" @click="load">다시 불러오기</button></p>
    <p v-if="notice" class="notice" role="status">{{ notice }}</p>
    <p v-if="loading" class="muted" role="status">학습 기록을 불러오는 중…</p>
    <section v-else-if="draft" class="study-view">
      <button class="back-link" :disabled="submitting || pending" @click="leave">← 달력으로 돌아가기</button>
      <p class="eyebrow">{{ draft.kind === 'new' ? 'NEW WORDS' : 'REVIEW' }}</p>
      <h1>{{ draft.kind === 'new' ? '새 단어와 만나는 시간' : '지난 단어를 다시 만나요' }}</h1>
      <p class="muted">{{ draft.kind === 'new' ? '뜻과 예문을 확인하고 학습 완료를 누르면 한 단어씩 저장돼요.' : '뜻을 떠올린 뒤 확인해 보세요. 기억 여부를 누르면 한 단어씩 저장돼요.' }}</p>
      <p v-if="today" class="muted" aria-label="오늘 저장한 학습">오늘 총 {{ savedToday }}개 · 신규 {{ today.new_count }}개 · 복습 {{ today.review_count }}개</p>
      <WordCard v-if="current" :word="current" :flipped="flipped" :disabled="submitting || pending" @flip="flipped = !flipped" />
      <div class="card-actions">
        <button v-if="pending" class="primary" :disabled="submitting" @click="submit">{{ submitting ? '저장하는 중…' : '저장 다시 시도' }}</button>
        <template v-else-if="current && flipped">
          <button v-if="draft.kind === 'new'" class="primary" @click="mark(null)">학습 완료</button>
          <template v-else><button class="secondary" @click="mark(false)">기억 안 나요</button><button class="primary" @click="mark(true)">기억나요</button></template>
        </template>
      </div>
    </section>
    <template v-else-if="today">
      <header class="intro"><div><p class="eyebrow">MY WORD JOURNAL</p><h1>공부한 날이 쌓이는 곳</h1><p class="muted">많이 해도, 조금 해도 괜찮아요. 오늘의 단어를 만나볼까요?</p></div><div class="total"><strong>{{ progress?.learned_count.toLocaleString() }}</strong><span>학습한 단어</span></div></header>
      <div class="dashboard">
        <section class="panel calendar-panel" aria-label="학습 달력">
          <div class="calendar-head"><h2>{{ monthTitle }}</h2><div class="month-controls"><button aria-label="이전 달" @click="moveMonth(-1)">‹</button><button aria-label="다음 달" @click="moveMonth(1)">›</button></div></div>
          <div class="calendar-grid weekdays"><span v-for="day in ['일','월','화','수','목','금','토']" :key="day">{{ day }}</span></div>
          <div class="calendar-grid">
            <template v-for="(day, i) in days" :key="i">
              <button v-if="day" class="day" :class="{ selected: selected === day.date, today: today.date === day.date, studied: !!day.record }"
                :aria-label="`${day.date}${day.record ? ' 학습 기록 있음' : ''}`" :aria-pressed="selected === day.date" :aria-current="today.date === day.date ? 'date' : undefined" @click="selectDay(day.date)">
                <span>{{ day.n }}</span><span class="study-dot" :class="{ filled: !!day.record }" />
              </button><span v-else />
            </template>
          </div>
          <div class="calendar-legend"><span class="study-dot filled" /> 공부한 날 <span class="today-legend">밑줄은 오늘</span></div>
        </section>
        <aside class="learning-options">
          <section class="start-panel"><p class="eyebrow">AT YOUR OWN PACE</p><h2>오늘도, 나의 속도로</h2><p>{{ today.new.length ? '지난 진도에서 이어서 시작해요. 하루에 몇 개든 자유롭게.' : '모든 새 단어를 학습했어요. 남은 복습과 기록을 확인해 보세요.' }}</p><button v-if="today.new.length" class="primary" @click="start('new')">새 단어 배우기 <span>↗</span></button></section>
          <section v-if="today.review_total" class="panel review-panel"><span class="review-tag">지난 학습 돌아보기</span><h2>{{ today.review_source_date?.slice(5).replace('-', '월 ') }}일에 배운 단어</h2><p class="muted">{{ today.review_total }}개 중 {{ today.review_completed }}개 복습 완료</p><template v-if="today.review.length"><p>기억을 한 번 꺼내볼까요?<br>복습은 원할 때 선택하면 돼요.</p><button class="secondary" @click="start('review')">{{ today.review_completed ? '복습 이어하기' : '복습하기' }} →</button></template><p v-else class="muted">이날의 단어를 모두 복습했어요.</p></section>
          <section v-else class="panel review-panel"><span class="review-tag">작은 시작</span><p>오늘 배운 단어는 다음에 왔을 때<br>다시 만나볼 수 있어요.</p></section>
        </aside>
        <section class="panel day-detail" aria-label="날짜별 학습 기록"><div class="detail-head"><h2>{{ selected.slice(5).replace('-', '월 ') }}일의 기록</h2><span v-if="detail?.results.length" class="muted">신규 {{ detail.results.filter(r => r.kind === 'new').length }} · 복습 {{ detail.results.filter(r => r.kind === 'review').length }}</span></div>
          <p v-if="!detail" class="muted">기록을 불러오는 중…</p><div v-else-if="!detail.results.length" class="empty"><span>◌</span><p>아직 학습 기록이 없는 날이에요.</p><small>공부한 날에는 이곳에 단어가 남아요.</small></div>
          <ul v-else class="word-list"><li v-for="(word, i) in detail.results" :key="i"><div><strong>{{ word.word }}</strong><p>{{ word.meaning }}</p></div><span class="word-kind">{{ word.kind === 'new' ? '신규 · 학습 완료' : `복습 · ${word.known === null ? '평가 없음' : word.known ? '기억나요' : '기억 안 나요'}` }}</span></li></ul>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.intro { display: flex; justify-content: space-between; align-items: center; gap: 24px; margin-bottom: 30px; }.intro p { margin-bottom: 0; }.total { display: grid; gap: 6px; text-align: right; flex-shrink: 0; }.total strong { font-size: 36px; font-family: Georgia, serif; font-weight: 500; }.total span { font-size: 13px; color: #758075; }
.dashboard { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(0, 1fr); gap: 24px; align-items: start; }.calendar-head,.detail-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; }.calendar-head h2 { margin: 0; }.month-controls { display: flex; gap: 6px; }.month-controls button { width: 36px; height: 36px; border: 1px solid #e1e3d9; border-radius: 50%; background: transparent; font-size: 25px; color: #284c3e; }.calendar-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 5px; }.weekdays { text-align: center; margin: 26px 0 12px; color: #8b9287; font-size: 12px; }.day { border: 0; border-radius: 13px; background: transparent; color: #445548; min-height: 58px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; }.day:hover { background: #f1f3ea; }.day.today > span:first-child { text-decoration: underline; text-underline-offset: 4px; font-weight: 750; }.day.studied { background: #eef2e8; }.day.selected { background: #284c3e; color: white; }.study-dot { display: inline-block; width: 5px; height: 5px; border-radius: 50%; background: transparent; }.study-dot.filled { background: #739269; }.selected .filled { background: #d6e8b4; }.calendar-legend { display: flex; align-items: center; gap: 8px; border-top: 1px solid #eceee4; padding-top: 18px; margin-top: 16px; color: #7e877a; font-size: 11px; }.today-legend { margin-left: auto; }.learning-options { display: grid; gap: 18px; }.start-panel { background: #e6ebdb; padding: 26px; border-radius: 20px; }.start-panel h2 { font-size: 23px; margin: 14px 0 10px; }.start-panel p:not(.eyebrow) { font-size: 14px; color: #65725e; }.start-panel button { width: 100%; text-align: left; margin-top: 14px; }.start-panel button span { float: right; }.review-tag { color: #8b7456; font-size: 12px; }.review-panel h2 { font-size: 17px; }.review-panel p { font-size: 14px; }.review-panel button { width: 100%; }.day-detail { grid-column: 1 / -1; }.detail-head h2 { margin: 0; font-size: 18px; }.detail-head > span { font-size: 13px; }.empty { text-align: center; padding: 26px 0 14px; color: #909789; }.empty > span { font-size: 32px; }.empty p { margin: 6px 0; font-size: 14px; }.empty small { font-size: 12px; }.word-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 28px; padding: 0; list-style: none; }.word-list li { display: flex; justify-content: space-between; align-items: center; gap: 12px; border-top: 1px solid #eceee4; padding: 16px 0; overflow-wrap: anywhere; }.word-list strong { font-family: Georgia, serif; font-size: 20px; }.word-list p { font-size: 13px; color: #758075; margin: 6px 0 0; }.word-kind { flex-shrink: 0; font-size: 11px; color: #8b7456; }.notice { border-left: 3px solid #739269; padding: 8px 14px; background: #edf2e6; }.study-view { max-width: 620px; margin: auto; }.back-link { border: 0; background: transparent; padding: 0; color: #73826c; margin: 0 0 28px; }.deck-progress { height: 5px; background: #e1e5d8; margin: 24px 0; border-radius: 4px; overflow: hidden; }.deck-progress span { display: block; height: 100%; background: #739269; }.card-actions { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-top: 24px; }.finish { text-align: center; padding: 48px 20px; }
@media(max-width: 760px) { .dashboard { grid-template-columns: 1fr; gap: 18px; }.learning-options { grid-template-columns: repeat(2, minmax(0, 1fr)); }.intro { align-items: flex-start; }.intro .muted { font-size: 14px; }.total strong { font-size: 28px; }.word-list { grid-template-columns: 1fr; } }
@media(max-width: 480px) { .intro { display: block; }.total { display: flex; text-align: left; align-items: baseline; margin-top: 18px; gap: 8px; }.learning-options { grid-template-columns: 1fr; }.day { min-height: 46px; }.calendar-grid { gap: 3px; }.detail-head { flex-wrap: wrap; }.start-panel { padding: 22px; } }
</style>
