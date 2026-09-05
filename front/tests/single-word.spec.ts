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
    const vocabulary = [word(1, 'remember'), word(2, 'interconnectedness'), word(3, 'thoughtful')]
    const records: { kind: string; rank: number; known: boolean | null }[] = []
    const requests: SubmitIn[] = []
    const saved = new Set<string>()
    let loseResponse = true
    let conflict = false
    const today = () => ({ date: '2026-09-05',
      new: vocabulary.slice(1).filter(w => !records.some(r => r.kind === 'new' && r.rank === w.rank)),
      review: records.some(r => r.kind === 'review') ? [] : vocabulary.slice(0, 1),
      review_source_date: '2026-09-03', review_total: 1,
      review_completed: records.filter(r => r.kind === 'review').length })
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
        await route.fulfill({ json: { total_words: 3, learned_count: 1 + records.filter(r => r.kind === 'new').length,
          next_rank: today().new[0]?.rank ?? 4, last_study_date: '2026-09-05', study_days: 2, undated_learned_count: 0 } }); return
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
    await expect(page.getByRole('button', { name: '학습 완료', exact: true })).toHaveCount(0)
    await page.getByRole('button', { name: '카드 뒤집기', exact: true }).click()
    await expect(page.getByRole('button', { name: '기억나요', exact: true })).toHaveCount(0)
    await mkdir('../docs/screenshots', { recursive: true })
    await page.screenshot({ path: `../docs/screenshots/single-word-new-${width}.png`, fullPage: true })
    await expect(page.locator('body')).toHaveJSProperty('scrollWidth', width)
    await page.getByRole('button', { name: '학습 완료', exact: true }).click()
    await expect(page.getByRole('alert')).toBeVisible()
    expect(requests[0]?.results).toEqual([{ rank: 2, known: null }])
    await expect(page.getByRole('button', { name: '← 달력으로 돌아가기', exact: true })).toBeDisabled()
    await page.reload()
    await page.getByRole('button', { name: '저장 다시 시도', exact: true }).click()
    await expect(page.getByText('thoughtful', { exact: true })).toBeVisible()
    expect(requests[1]).toEqual(requests[0])
    expect(records).toHaveLength(1)
    await page.getByRole('button', { name: '← 달력으로 돌아가기', exact: true }).click()
    await expect(page.getByText('신규 1 · 복습 0')).toBeVisible()
    await page.getByRole('button', { name: '복습하기 →', exact: true }).click()
    await page.getByRole('button', { name: '카드 뒤집기', exact: true }).click()
    await expect(page.getByRole('button', { name: '학습 완료', exact: true })).toHaveCount(0)
    await expect(page.getByRole('button', { name: '기억나요', exact: true })).toBeVisible()
    await page.screenshot({ path: `../docs/screenshots/single-word-review-${width}.png`, fullPage: true })
    await page.getByRole('button', { name: '기억 안 나요', exact: true }).click()
    await expect(page.getByText('신규 1 · 복습 1')).toBeVisible()
    await expect(page.getByText('복습 · 기억 안 나요', { exact: true })).toBeVisible()
    expect(requests[2]?.results).toEqual([{ rank: 1, known: false }])
    await page.screenshot({ path: `../docs/screenshots/single-word-calendar-${width}.png`, fullPage: true })
    await expect(page.locator('body')).toHaveJSProperty('scrollWidth', width)
    // An unsaved stale card must not advance progress or trap the user in retry.
    conflict = true
    await page.getByRole('button', { name: '새 단어 배우기' }).click()
    await page.getByRole('button', { name: '카드 뒤집기', exact: true }).click()
    await page.getByRole('button', { name: '학습 완료', exact: true }).click()
    await expect(page.getByRole('status').filter({ hasText: '날짜가 바뀌었습니다.' })).toBeVisible()
    await expect(page.getByText('신규 1 · 복습 1')).toBeVisible()
    expect(records).toHaveLength(2)
  })
}
