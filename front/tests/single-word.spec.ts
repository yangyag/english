import { test, expect } from '@playwright/test'
import { mkdir } from 'node:fs/promises'
import type { SubmitIn, WordOut } from '../types/api'

// Synthetic API responses only. Run independently of the PostgreSQL integration test.
for (const width of [1440, 375]) {
  test(`single-word controls and interrupted save at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 1100 })
    const word = (rank: number, term: string): WordOut => ({ rank, word: term,
      meaning: '서로 연결되어 있음; 상호 연결성',
      example: 'The interconnectedness of small everyday choices reminds us that learning grows through patient practice, curiosity, and the willingness to begin again, even after a long pause.',
      example_ko: '작은 일상의 선택들은 서로 연결되어 있고 꾸준한 연습이 배움을 키워 준다.' })
    const vocabulary = [word(1, 'remember'), word(2, 'interconnectedness'), word(3, 'thoughtful'),
      word(4, 'curiosity'), word(5, 'delight'), word(6, 'breathe')]
    const records: { kind: string; rank: number; known: boolean | null }[] = []
    const requests: SubmitIn[] = []
    const saved = new Set<string>()
    let loseResponse = true
    let conflict = false
    const today = () => ({ date: '2026-09-05',
      new: vocabulary.slice(1).filter(w => !records.some(r => r.kind === 'new' && r.rank === w.rank)),
      review: records.some(r => r.kind === 'review') ? [] : vocabulary.slice(0, 1),
      review_source_date: '2026-09-03', review_total: 1,
      review_completed: records.filter(r => r.kind === 'review').length,
      new_count: records.filter(r => r.kind === 'new').length,
      review_count: records.filter(r => r.kind === 'review').length })
    const savedToday = page.getByLabel('오늘 저장한 학습', { exact: true })
    async function expectCardCounts(newCount: number, reviewCount: number) {
      await expect(savedToday).toHaveText(`오늘 총 ${newCount + reviewCount}개 · 신규 ${newCount}개 · 복습 ${reviewCount}개`)
    }
    async function expectNotice(total: number, final = false) {
      await expect(page.getByRole('status').filter({ hasText: '학습을 저장했어요.' })).toHaveText(final
        ? `학습을 모두 마쳤어요. 오늘 ${total}개 학습을 저장했어요.`
        : `오늘 ${total}개 학습을 저장했어요. 언제든 돌아가도 기록은 남아요.`)
    }
    await page.route('**/v1/**', async route => {
      const path = new URL(route.request().url()).pathname
      if (route.request().method() === 'POST') {
        const body = route.request().postDataJSON() as SubmitIn
        requests.push(body)
        if (conflict) { await route.fulfill({ status: 409, json: { detail: '날짜가 바뀌었습니다.' } }); return }
        if (!saved.has(body.request_id)) {
          saved.add(body.request_id)
          records.push(...body.results.map(r => ({ ...r, kind: path.endsWith('/new') ? 'new' : 'review' })))
        }
        if (loseResponse) { loseResponse = false; await route.abort('failed'); return }
        await route.fulfill({ json: today() }); return
      }
      if (path === '/v1/today') { await route.fulfill({ json: today() }); return }
      if (path === '/v1/progress') {
        await route.fulfill({ json: { total_words: vocabulary.length, learned_count: 1 + records.filter(r => r.kind === 'new').length,
          next_rank: today().new[0]?.rank ?? vocabulary.length + 1, last_study_date: '2026-09-05', study_days: 2, undated_learned_count: 0 } }); return
      }
      if (path === '/v1/calendar') {
        await route.fulfill({ json: { month: '2026-09', days: records.length ? [{ date: '2026-09-05',
          new_count: records.filter(r => r.kind === 'new').length, review_count: records.filter(r => r.kind === 'review').length }] : [] } }); return
      }
      if (path.startsWith('/v1/calendar/')) {
        await route.fulfill({ json: { date: '2026-09-05', results: records.map(r => ({ ...vocabulary.find(w => w.rank === r.rank), ...r })) } }); return
      }
      await route.abort()
    })
    await page.goto('/')
    await page.getByRole('button', { name: '새 단어 배우기' }).click()
    await expectCardCounts(0, 0)
    await expect(page.getByRole('button', { name: '학습 완료', exact: true })).toHaveCount(0)
    await page.getByRole('button', { name: '카드 뒤집기', exact: true }).click()
    await expectCardCounts(0, 0)
    await expect(page.getByRole('button', { name: '기억나요', exact: true })).toHaveCount(0)
    await mkdir('../docs/screenshots', { recursive: true })
    await page.screenshot({ path: `../docs/screenshots/single-word-new-${width}.png`, fullPage: true })
    await expect(page.locator('body')).toHaveJSProperty('scrollWidth', width)
    await page.getByRole('button', { name: '학습 완료', exact: true }).click()
    await expect(page.getByRole('alert')).toBeVisible()
    expect(requests[0]?.results).toEqual([{ rank: 2, known: null }])
    expect(records).toHaveLength(1)
    await expectCardCounts(0, 0)
    await expect(page.getByRole('status').filter({ hasText: '학습을 저장했어요.' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: '← 달력으로 돌아가기', exact: true })).toBeDisabled()
    await page.reload()
    await expectCardCounts(1, 0)
    await page.getByRole('button', { name: '저장 다시 시도', exact: true }).click()
    await expect(page.getByText('thoughtful', { exact: true })).toBeVisible()
    await expectCardCounts(1, 0)
    await expectNotice(1)
    expect(requests[1]).toEqual(requests[0])
    expect(records).toHaveLength(1)
    for (const newCount of [2, 3]) {
      await page.getByRole('button', { name: '카드 뒤집기', exact: true }).click()
      await expectCardCounts(newCount - 1, 0)
      await page.getByRole('button', { name: '학습 완료', exact: true }).click()
      await expectCardCounts(newCount, 0)
      await expectNotice(newCount)
      expect(records).toHaveLength(newCount)
      expect(requests[newCount]?.results).toEqual([{ rank: newCount + 1, known: null }])
    }
    await page.getByRole('button', { name: '← 달력으로 돌아가기', exact: true }).click()
    await expect(page.getByText('신규 3 · 복습 0')).toBeVisible()
    await page.getByRole('button', { name: '새 단어 배우기' }).click()
    await expectCardCounts(3, 0)
    await page.reload()
    await expect(page.getByText('delight', { exact: true })).toBeVisible()
    await expectCardCounts(3, 0)
    await page.getByRole('button', { name: '← 달력으로 돌아가기', exact: true }).click()
    await page.getByRole('button', { name: '복습하기 →', exact: true }).click()
    await expectCardCounts(3, 0)
    await page.getByRole('button', { name: '카드 뒤집기', exact: true }).click()
    await expect(page.getByRole('button', { name: '학습 완료', exact: true })).toHaveCount(0)
    await expect(page.getByRole('button', { name: '기억나요', exact: true })).toBeVisible()
    await page.screenshot({ path: `../docs/screenshots/single-word-review-${width}.png`, fullPage: true })
    await page.getByRole('button', { name: '기억 안 나요', exact: true }).click()
    await expect(page.getByText('신규 3 · 복습 1')).toBeVisible()
    await expectNotice(4, true)
    await expect(page.getByText('복습 · 기억 안 나요', { exact: true })).toBeVisible()
    expect(requests[4]?.results).toEqual([{ rank: 1, known: false }])
    await page.screenshot({ path: `../docs/screenshots/single-word-calendar-${width}.png`, fullPage: true })
    await expect(page.locator('body')).toHaveJSProperty('scrollWidth', width)
    // An unsaved stale card must not advance progress or trap the user in retry.
    conflict = true
    await page.getByRole('button', { name: '새 단어 배우기' }).click()
    await expectCardCounts(3, 1)
    await page.getByRole('button', { name: '카드 뒤집기', exact: true }).click()
    await page.getByRole('button', { name: '학습 완료', exact: true }).click()
    await expect(page.getByRole('status').filter({ hasText: '날짜가 바뀌었습니다.' })).toBeVisible()
    await expect(page.getByText('신규 3 · 복습 1')).toBeVisible()
    await expect(page.getByRole('status').filter({ hasText: '학습을 저장했어요.' })).toHaveCount(0)
    expect(records).toHaveLength(4)
    conflict = false
    await page.getByRole('button', { name: '새 단어 배우기' }).click()
    await expect(page.getByText('delight', { exact: true })).toBeVisible()
    await expectCardCounts(3, 1)
    await page.getByRole('button', { name: '카드 뒤집기', exact: true }).click()
    await page.getByRole('button', { name: '학습 완료', exact: true }).click()
    await expectCardCounts(4, 1)
    await expectNotice(5)
    await page.reload()
    await expect(page.getByText('breathe', { exact: true })).toBeVisible()
    await expectCardCounts(4, 1)
    await page.getByRole('button', { name: '카드 뒤집기', exact: true }).click()
    await page.getByRole('button', { name: '학습 완료', exact: true }).click()
    await expect(page.getByText('신규 5 · 복습 1')).toBeVisible()
    await expectNotice(6, true)
    await expect(savedToday).toHaveCount(0)
    expect(records).toHaveLength(6)
    await page.reload()
    await expect(page.getByText('신규 5 · 복습 1')).toBeVisible()
    await expect(page.getByRole('button', { name: '새 단어 배우기' })).toHaveCount(0)
  })
}

test('yesterday’s committed retry uses today’s server count without moving the record', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 })
  await page.clock.setFixedTime(new Date('2026-09-05T03:00:00Z'))
  const vocabulary: WordOut[] = ['remember', 'thoughtful'].map((word, i) => ({
    rank: i + 1, word, meaning: '기억하고 싶은 단어', example: `I want to ${word}.`, example_ko: '기억하고 싶은 예문.' }))
  let serverDate = '2026-09-05'
  let loseResponse = true
  const records: { date: string; rank: number; known: boolean | null }[] = []
  const requests: SubmitIn[] = []
  const saved = new Set<string>()
  const today = () => {
    const review = vocabulary.filter(w => records.some(r => r.date < serverDate && r.rank === w.rank))
    return { date: serverDate,
      new: vocabulary.filter(w => !records.some(r => r.rank === w.rank)), review,
      review_source_date: review.length ? '2026-09-05' : null,
      review_total: review.length, review_completed: 0,
      new_count: records.filter(r => r.date === serverDate).length, review_count: 0 }
  }
  await page.route('**/v1/**', async route => {
    const path = new URL(route.request().url()).pathname
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON() as SubmitIn
      requests.push(body)
      if (!saved.has(body.request_id)) {
        if (body.study_date !== serverDate) {
          await route.fulfill({ status: 409, json: { detail: '날짜가 바뀌었습니다.' } }); return
        }
        saved.add(body.request_id)
        records.push(...body.results.map(r => ({ ...r, date: serverDate })))
      }
      if (loseResponse) { loseResponse = false; await route.abort('failed'); return }
      await route.fulfill({ json: today() }); return
    }
    if (path === '/v1/today') { await route.fulfill({ json: today() }); return }
    if (path === '/v1/progress') {
      await route.fulfill({ json: { total_words: vocabulary.length, learned_count: records.length,
        next_rank: today().new[0]?.rank ?? vocabulary.length + 1, last_study_date: records.at(-1)?.date ?? null,
        study_days: new Set(records.map(r => r.date)).size, undated_learned_count: 0 } }); return
    }
    if (path === '/v1/calendar') {
      await route.fulfill({ json: { month: '2026-09', days: [...new Set(records.map(r => r.date))].map(date => ({
        date, new_count: records.filter(r => r.date === date).length, review_count: 0 })) } }); return
    }
    if (path.startsWith('/v1/calendar/')) {
      const date = path.slice('/v1/calendar/'.length)
      await route.fulfill({ json: { date, results: records.filter(r => r.date === date).map(r => ({
        ...vocabulary.find(w => w.rank === r.rank), kind: 'new', known: r.known })) } }); return
    }
    await route.abort()
  })
  const savedToday = page.getByLabel('오늘 저장한 학습', { exact: true })
  await page.goto('/')
  await page.getByRole('button', { name: '새 단어 배우기' }).click()
  await expect(savedToday).toHaveText('오늘 총 0개 · 신규 0개 · 복습 0개')
  await page.getByRole('button', { name: '카드 뒤집기', exact: true }).click()
  await page.getByRole('button', { name: '학습 완료', exact: true }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(savedToday).toHaveText('오늘 총 0개 · 신규 0개 · 복습 0개')
  expect(records).toEqual([{ date: '2026-09-05', rank: 1, known: null }])
  serverDate = '2026-09-06'
  await page.reload()
  await expect(savedToday).toHaveText('오늘 총 0개 · 신규 0개 · 복습 0개')
  const retryResponse = page.waitForResponse(r => r.url().endsWith('/v1/today/new') && r.request().method() === 'POST')
  await page.getByRole('button', { name: '저장 다시 시도', exact: true }).click()
  expect(await (await retryResponse).json()).toMatchObject({ date: '2026-09-06', new_count: 0, review_count: 0 })
  await expect(page.getByText('thoughtful', { exact: true })).toBeVisible()
  await expect(savedToday).toHaveText('오늘 총 0개 · 신규 0개 · 복습 0개')
  await expect(page.getByRole('status').filter({ hasText: '학습을 저장했어요.' }))
    .toHaveText('오늘 0개 학습을 저장했어요. 언제든 돌아가도 기록은 남아요.')
  expect(requests).toHaveLength(2)
  expect(requests[1]).toEqual(requests[0])
  expect(requests[1]?.study_date).toBe('2026-09-05')
  expect(records).toEqual([{ date: '2026-09-05', rank: 1, known: null }])
  await page.getByRole('button', { name: '← 달력으로 돌아가기', exact: true }).click()
  await expect(page.getByRole('button', { name: '2026-09-06', exact: true })).toHaveAttribute('aria-current', 'date')
  await expect(page.getByText('아직 학습 기록이 없는 날이에요.')).toBeVisible()
  await page.getByRole('button', { name: '2026-09-05 학습 기록 있음', exact: true }).click()
  await expect(page.getByText('신규 1 · 복습 0')).toBeVisible()
  await expect(page.getByRole('region', { name: '날짜별 학습 기록', exact: true }).getByText('remember', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '새 단어 배우기' }).click()
  await expect(savedToday).toHaveText('오늘 총 0개 · 신규 0개 · 복습 0개')
  await page.reload()
  await expect(savedToday).toHaveText('오늘 총 0개 · 신규 0개 · 복습 0개')
})
