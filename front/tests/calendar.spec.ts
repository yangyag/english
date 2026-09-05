import { test, expect } from '@playwright/test'
import { mkdir } from 'node:fs/promises'
import type { CalendarOut, DayOut, TodayOut } from '../types/api'
const screenshots = '../docs/screenshots'

test('single-word learning, retry, review resume and mobile layout', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  let newCount = 0
  let reviewCount = 0
  const savedToday = page.getByLabel('오늘 저장한 학습', { exact: true })
  async function expectCardCounts(expectedNew = newCount, expectedReview = reviewCount) {
    await expect(savedToday).toHaveText(`오늘 총 ${expectedNew + expectedReview}개 · 신규 ${expectedNew}개 · 복습 ${expectedReview}개`)
  }
  async function expectServerCounts(expectedNew = newCount, expectedReview = reviewCount) {
    const response = await page.request.get('/v1/today')
    expect(response.status()).toBe(200)
    expect(await response.json()).toMatchObject({ date: '2026-09-05', new_count: expectedNew, review_count: expectedReview })
  }
  async function expectNotice(final = false) {
    await expect(page.getByRole('status').filter({ hasText: '학습을 저장했어요.' })).toHaveText(final
      ? `학습을 모두 마쳤어요. 오늘 ${newCount + reviewCount}개 학습을 저장했어요.`
      : `오늘 ${newCount + reviewCount}개 학습을 저장했어요. 언제든 돌아가도 기록은 남아요.`)
  }
  async function answer(count: number, review = false) {
    const kind = review ? 'review' : 'new'
    for (let i = 0; i < count; i++) {
      await expectCardCounts()
      await page.getByRole('button', { name: '카드 뒤집기', exact: true }).click()
      await expectCardCounts()
      const response = page.waitForResponse(r => r.url().endsWith(`/v1/today/${kind}`) && r.request().method() === 'POST')
      await page.getByRole('button', { name: review ? (i % 2 ? '기억 안 나요' : '기억나요') : '학습 완료', exact: true }).click()
      const result = await response
      expect(result.status()).toBe(200)
      const data = await result.json() as TodayOut
      if (review) reviewCount++; else newCount++
      expect(data).toMatchObject({ date: '2026-09-05', new_count: newCount, review_count: reviewCount })
      await expectServerCounts()
      await expect(page.getByRole('button', { name: '저장하는 중…', exact: true })).toHaveCount(0)
      await expectNotice(data[kind].length === 0)
      if (data[kind].length) await expectCardCounts()
      else await expect(page.getByText(`신규 ${newCount} · 복습 ${reviewCount}`, { exact: true })).toBeVisible()
    }
  }
  await mkdir(screenshots, { recursive: true })
  await page.setViewportSize({ width: 1440, height: 1100 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '공부한 날이 쌓이는 곳' })).toBeVisible()
  await expect(page.getByText('20개 중 0개 복습 완료')).toBeVisible()
  await expectServerCounts()
  await page.screenshot({ path: `${screenshots}/calendar-desktop.png`, fullPage: true })
  await page.setViewportSize({ width: 375, height: 812 })
  await page.screenshot({ path: `${screenshots}/calendar-mobile-initial.png`, fullPage: true })
  await page.setViewportSize({ width: 1440, height: 1100 })
  await page.getByRole('button', { name: '2026-09-03 학습 기록 있음', exact: true }).click()
  await expect(page.getByText('신규 20 · 복습 0')).toBeVisible()
  await page.getByRole('button', { name: '이전 달', exact: true }).click()
  await expect(page.getByRole('heading', { name: '2026년 8월' })).toBeVisible()
  await page.getByRole('button', { name: '다음 달', exact: true }).click()
  await expect(page.getByRole('heading', { name: '2026년 9월' })).toBeVisible()
  await page.getByRole('button', { name: '새 단어 배우기' }).click()
  await expect(page.getByText('interconnectedness', { exact: true })).toBeVisible()
  await expectCardCounts()
  await page.setViewportSize({ width: 375, height: 812 })
  await page.getByRole('button', { name: '카드 뒤집기', exact: true }).click()
  await expectCardCounts()
  await expect(page.getByText('서로 연결되어 있음; 상호 연결성')).toBeVisible()
  await page.screenshot({ path: `${screenshots}/card-mobile.png`, fullPage: true })
  await expect(page.locator('body')).toHaveJSProperty('scrollWidth', 375)
  await expect(page.getByRole('button', { name: '기억나요', exact: true })).toHaveCount(0)
  const firstResponse = page.waitForResponse(r => r.url().endsWith('/v1/today/new') && r.request().method() === 'POST')
  await page.getByRole('button', { name: '학습 완료', exact: true }).click()
  const firstResult = await firstResponse
  expect(firstResult.status()).toBe(200)
  newCount = 1
  expect(await firstResult.json()).toMatchObject({ new_count: 1, review_count: 0 })
  await expect(page.getByText('thoughtful', { exact: true })).toBeVisible()
  await expectCardCounts()
  await expectNotice()
  await expectServerCounts()
  await page.reload()
  await expect(page.getByText('thoughtful', { exact: true })).toBeVisible()
  await expectCardCounts()
  await page.getByRole('button', { name: '← 달력으로 돌아가기', exact: true }).click()
  await expect(page.getByText('신규 1 · 복습 0')).toBeVisible()
  await expect(page.getByText('신규 · 학습 완료', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '새 단어 배우기' }).click()
  await expectCardCounts()
  // Simulate an ambiguous response: the backend commits, the browser loses it.
  let committedRequest: unknown
  await page.route('**/v1/today/new', async route => {
    committedRequest = route.request().postDataJSON()
    const response = await route.fetch()
    expect(response.status()).toBe(200)
    expect(await response.json()).toMatchObject({ new_count: 2, review_count: 0 })
    await route.abort('failed')
  }, { times: 1 })
  await page.getByRole('button', { name: '카드 뒤집기', exact: true }).click()
  await page.getByRole('button', { name: '학습 완료', exact: true }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await expect(page.locator('.term', { hasText: 'thoughtful' })).toBeVisible()
  await expectCardCounts(1, 0)
  await expect(page.getByRole('status').filter({ hasText: '오늘 2개 학습을 저장했어요.' })).toHaveCount(0)
  await expectServerCounts(2, 0)
  await expect(page.getByRole('button', { name: '← 달력으로 돌아가기', exact: true })).toBeDisabled()
  await page.reload()
  newCount = 2
  await expectCardCounts()
  const retryResponse = page.waitForResponse(r => r.url().endsWith('/v1/today/new') && r.request().method() === 'POST')
  await page.getByRole('button', { name: '저장 다시 시도', exact: true }).click()
  const retryResult = await retryResponse
  expect(retryResult.status()).toBe(200)
  expect(retryResult.request().postDataJSON()).toEqual(committedRequest)
  expect(await retryResult.json()).toMatchObject({ new_count: 2, review_count: 0 })
  await expect(page.getByText('curiosity', { exact: true })).toBeVisible()
  await expectCardCounts()
  await expectNotice()
  await expectServerCounts()
  await page.getByRole('button', { name: '← 달력으로 돌아가기', exact: true }).click()
  await expect(page.getByText('신규 2 · 복습 0')).toBeVisible()
  await expect(page.getByText('20개 중 0개 복습 완료')).toBeVisible()
  await page.getByRole('button', { name: '복습하기 →', exact: true }).click()
  await expectCardCounts()
  await answer(1, true)
  await page.getByRole('button', { name: '← 달력으로 돌아가기', exact: true }).click()
  await expect(page.getByText('신규 2 · 복습 1')).toBeVisible()
  await expect(page.getByText('복습 · 기억나요', { exact: true })).toBeVisible()
  await page.reload()
  await expectServerCounts()
  await page.getByRole('button', { name: '복습 이어하기 →', exact: true }).click()
  await expect(page.getByText('wander', { exact: true })).toBeVisible()
  await expectCardCounts()
  await answer(19, true)
  expect([newCount, reviewCount]).toEqual([2, 20])
  await expect(page.getByText('이날의 단어를 모두 복습했어요.')).toBeVisible()
  await expectNotice(true)
  await page.getByRole('button', { name: '새 단어 배우기' }).click()
  await expectCardCounts()
  await answer(13)
  expect([newCount, reviewCount]).toEqual([15, 20])
  await expect(page.getByText('신규 15 · 복습 20')).toBeVisible()
  await expectNotice(true)
  await expect(savedToday).toHaveCount(0)
  await expect(page.getByRole('button', { name: '새 단어 배우기' })).toHaveCount(0)
  await page.screenshot({ path: `${screenshots}/calendar-mobile.png`, fullPage: true })
  await expect(page.locator('body')).toHaveJSProperty('scrollWidth', 375)
  const calendarResponse = await page.request.get('/v1/calendar?month=2026-09')
  expect(calendarResponse.status()).toBe(200)
  const calendar = await calendarResponse.json() as CalendarOut
  expect(calendar.days).toEqual(expect.arrayContaining([
    { date: '2026-09-03', new_count: 20, review_count: 0 },
    { date: '2026-09-05', new_count: 15, review_count: 20 },
  ]))
  const dayResponse = await page.request.get('/v1/calendar/2026-09-05')
  expect(dayResponse.status()).toBe(200)
  const detail = await dayResponse.json() as DayOut
  expect(detail.results).toHaveLength(35)
  expect(detail.results.filter(r => r.kind === 'new')).toHaveLength(15)
  expect(detail.results.filter(r => r.kind === 'review')).toHaveLength(20)
  await page.reload()
  await expect(page.getByText('신규 15 · 복습 20')).toBeVisible()
  await expectServerCounts()
  await page.getByRole('link', { name: '진도', exact: true }).click()
  await expect(page.getByText('35', { exact: true })).toBeVisible()
  await expect(page.getByText('2일', { exact: true })).toBeVisible()
  expect(errors).toEqual([])
})
